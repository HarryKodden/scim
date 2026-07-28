"""SCIM plugin that persists Users/Groups into the SRAM LDAP directory."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from ldap3 import ALL, Connection, Server, SUBTREE

from data.plugins import Plugin
from data.plugins.sram_ldap import dit, flat, mapping

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class SRAM_LDAP_Plugin(Plugin):
    """LDAP backend for ``LDAP_LAYOUT=sram-ordered``.

    * Users are written under each Collaboration's ``ou=People`` when they
      appear as members of a CO / group (and refreshed on User updates).
    * Groups: Collaboration resources create ``o=<org.co>`` + ``cn=@all``;
      subgroup resources create ``cn=<group>`` under that CO.
    * When ``LDAP_FLAT_DERIVE=true``, flat entries are projected after ordered
      writes.
    """

    def __init__(
        self,
        resource_type: str,
        ldap_hostname: str,
        ldap_basename: str,
        ldap_username: str,
        ldap_password: str,
        flat_derive: Optional[bool] = None,
    ):
        self.resource_type = resource_type
        self.ldap_basename = ldap_basename
        self.flat_derive = (
            _env_bool("LDAP_FLAT_DERIVE", True)
            if flat_derive is None
            else flat_derive
        )
        self.description = f"SRAM-LDAP-{resource_type}"

        server = Server(ldap_hostname, get_info=ALL)
        self.session = Connection(
            server,
            user=ldap_username,
            password=ldap_password,
            auto_bind=True,
        )
        logger.info("SRAM LDAP connected (%s)", self.description)
        self._ensure_roots()

    def _ensure_roots(self) -> None:
        self._ensure_entry(
            dit.ordered_base(self.ldap_basename),
            {
                "objectClass": ["dcObject", "organizationalUnit"],
                "dc": ["ordered"],
                "ou": ["ordered"],
            },
        )
        if self.flat_derive:
            self._ensure_entry(
                dit.flat_base(self.ldap_basename),
                {
                    "objectClass": ["dcObject", "organizationalUnit"],
                    "dc": ["flat"],
                    "ou": ["flat"],
                },
            )
            for ou in ("People", "Groups"):
                self._ensure_entry(
                    f"ou={ou},{dit.flat_base(self.ldap_basename)}",
                    {"objectClass": ["top", "organizationalUnit"], "ou": [ou]},
                )

    def _ensure_entry(self, dn: str, attributes: Dict[str, List[Any]]) -> None:
        if self.session.search(dn, "(objectClass=*)", search_scope="BASE"):
            return
        ok = self.session.add(dn, attributes=attributes)
        if not ok:
            logger.debug("ensure %s: %s", dn, self.session.result)

    def _ensure_co_containers(self, co_identifier: str) -> None:
        co_dn = dit.co_dn(co_identifier, self.ldap_basename)
        # Organization body is written by collaboration group upsert.
        if not self.session.search(co_dn, "(objectClass=*)", search_scope="BASE"):
            self._ensure_entry(
                co_dn,
                {
                    "objectClass": ["top", "organization", "extensibleObject"],
                    "o": [co_identifier],
                },
            )
        for ou in ("People", "Groups"):
            self._ensure_entry(
                f"ou={ou},{co_dn}",
                {"objectClass": ["top", "organizationalUnit"], "ou": [ou]},
            )

    def _upsert(self, dn: str, attributes: Dict[str, List[Any]]) -> None:
        if self.session.search(dn, "(objectClass=*)", search_scope="BASE", attributes=["*"]):
            changes = {
                attr: [("MODIFY_REPLACE", values)]
                for attr, values in attributes.items()
                if attr.lower() != "objectclass"
            }
            # objectClass may need replace as a whole when ssh keys appear
            changes["objectClass"] = [("MODIFY_REPLACE", attributes["objectClass"])]
            ok = self.session.modify(dn, changes)
        else:
            ok = self.session.add(dn, attributes=attributes)
        if not ok:
            raise RuntimeError(
                f"LDAP upsert failed for {dn}: {self.session.result}"
            )

    def _delete_if_exists(self, dn: str) -> None:
        if self.session.search(dn, "(objectClass=*)", search_scope="BASE"):
            self.session.delete(dn)

    def _search(self, base: str, ldap_filter: str, attributes=None) -> Dict[str, dict]:
        attributes = attributes or ["*"]
        result: Dict[str, dict] = {}
        entries = self.session.extend.standard.paged_search(
            search_base=base,
            search_filter=ldap_filter,
            search_scope=SUBTREE,
            attributes=attributes,
            paged_size=100,
            generator=True,
        )
        for entry in entries:
            if entry.get("type") != "searchResEntry":
                continue
            result[entry["dn"]] = entry["attributes"]
        return result

    def _member_uids(self, resource: dict) -> List[str]:
        """Resolve SCIM members to LDAP uids (look up User resources by id)."""
        uids: List[str] = []
        for member in resource.get("members") or []:
            member_id = member.get("value")
            if not member_id:
                continue
            user = self._load_user_by_id(member_id)
            if user and user.get("userName"):
                uids.append(user["userName"])
            else:
                logger.warning(
                    "Member %s not found as User; skipping DN resolution",
                    member_id,
                )
        return uids

    def _load_user_by_id(self, user_id: str) -> Optional[dict]:
        """Read a SCIM User from ordered People by externalId/cn or from sibling plugin.

        During group writes, Users may already exist under one or more COs.
        We search ordered tree for eduPersonUniqueId / cn matching the SCIM id.
        """
        # Prefer an already-written person entry
        people = self._search(
            dit.ordered_base(self.ldap_basename),
            f"(&(objectClass=person)(|(eduPersonUniqueId={user_id})(cn={user_id})))",
            attributes=["uid", "eduPersonUniqueId", "cn", "displayName"],
        )
        if people:
            attrs = next(iter(people.values()))
            uid = attrs.get("uid")
            uid_val = uid[0] if isinstance(uid, list) else uid
            return {"id": user_id, "userName": uid_val}

        # Fallback: if this instance is Groups, ask Users store via module
        try:
            from data import Users as users_store
            if users_store is not self:
                raw = users_store[user_id]
                if raw:
                    return raw
        except Exception as exc:
            logger.debug("Users lookup fallback failed: %s", exc)
        return None

    # --- Plugin API ---------------------------------------------------------

    def __iter__(self) -> Any:
        if self.resource_type == self.USERS:
            seen = set()
            people = self._search(
                dit.ordered_base(self.ldap_basename),
                "(objectClass=inetOrgPerson)",
                attributes=["eduPersonUniqueId", "cn"],
            )
            for attrs in people.values():
                key = attrs.get("eduPersonUniqueId") or attrs.get("cn")
                if isinstance(key, list):
                    key = key[0] if key else None
                if key and key not in seen:
                    seen.add(key)
                    yield key
        else:
            groups = self._search(
                dit.ordered_base(self.ldap_basename),
                "(objectClass=groupOfMembers)",
                attributes=["uniqueIdentifier", "cn"],
            )
            for dn, attrs in groups.items():
                uid = attrs.get("uniqueIdentifier")
                if isinstance(uid, list):
                    uid = uid[0] if uid else None
                if uid:
                    yield uid
                else:
                    # Fall back to DN-based synthetic id
                    yield dn

    def __delitem__(self, id: str) -> None:
        if self.resource_type == self.USERS:
            people = self._search(
                dit.ordered_base(self.ldap_basename),
                f"(&(objectClass=person)(|(eduPersonUniqueId={id})(cn={id})))",
            )
            for dn in people:
                self.session.delete(dn)
            if self.flat_derive:
                # Remove flat twin if present (uid unknown → search)
                flat_people = self._search(
                    dit.flat_base(self.ldap_basename),
                    f"(&(objectClass=person)(|(eduPersonUniqueId={id})(cn={id})))",
                )
                for dn in flat_people:
                    self.session.delete(dn)
            return

        groups = self._search(
            dit.ordered_base(self.ldap_basename),
            f"(&(objectClass=groupOfMembers)(uniqueIdentifier={id}))",
        )
        for dn in groups:
            self.session.delete(dn)
        if self.flat_derive:
            flat_groups = self._search(
                dit.flat_base(self.ldap_basename),
                f"(&(objectClass=groupOfMembers)(uniqueIdentifier={id}))",
            )
            for dn in flat_groups:
                self.session.delete(dn)

    def __getitem__(self, id: str) -> Any:
        if self.resource_type == self.USERS:
            return self._get_user(id)
        return self._get_group(id)

    def __setitem__(self, id: str, details: Any) -> None:
        resource = json.loads(details) if isinstance(details, str) else details
        resource = dict(resource)
        resource["id"] = id
        if self.resource_type == self.USERS:
            self._set_user(id, resource)
        else:
            self._set_group(id, resource)

    # --- Users --------------------------------------------------------------

    def _get_user(self, id: str) -> Optional[dict]:
        people = self._search(
            dit.ordered_base(self.ldap_basename),
            f"(&(objectClass=person)(|(eduPersonUniqueId={id})(cn={id})))",
            attributes=["*"],
        )
        if not people:
            return None
        attrs = next(iter(people.values()))
        uid = attrs.get("uid")
        uid_val = uid[0] if isinstance(uid, list) else uid
        mail = attrs.get("mail")
        mail_val = mail[0] if isinstance(mail, list) and mail else mail
        display = attrs.get("displayName")
        display_val = display[0] if isinstance(display, list) else display
        return {
            "id": id,
            "userName": uid_val,
            "displayName": display_val,
            "emails": [{"value": mail_val, "primary": True}] if mail_val else [],
            "active": (attrs.get("voPersonStatus") or ["active"])[0] == "active",
        }

    def _set_user(self, id: str, resource: dict) -> None:
        ldap_attrs = mapping.scim_user_to_ldap(resource)
        uid = ldap_attrs["uid"][0]

        # Refresh under every CO where this uid already exists; if none, stash
        # under no CO until a group membership write places the person.
        existing = self._search(
            dit.ordered_base(self.ldap_basename),
            f"(&(objectClass=person)(uid={uid}))",
        )
        if not existing:
            logger.info(
                "User %s (%s) stored mapping only after CO membership; "
                "no ordered People DN yet",
                id,
                uid,
            )
            # Keep a transient cache entry under a well-known holding OU so
            # group membership resolution can find userName by SCIM id.
            hold_ou = f"ou=People,{dit.ordered_base(self.ldap_basename)}"
            self._ensure_entry(
                hold_ou,
                {"objectClass": ["top", "organizationalUnit"], "ou": ["People"]},
            )
            hold_dn = f"uid={uid},{hold_ou}"
            # Annotate with SCIM id in cn/eduPersonUniqueId already in ldap_attrs
            self._upsert(hold_dn, ldap_attrs)
            return

        for dn in existing:
            self._upsert(dn, ldap_attrs)

        if self.flat_derive:
            self._derive_flat_person(uid, ldap_attrs)

    def _derive_flat_person(self, uid: str, ldap_attrs: Dict[str, List[Any]]) -> None:
        statuses = []
        people = self._search(
            dit.ordered_base(self.ldap_basename),
            f"(&(objectClass=person)(uid={uid}))",
            attributes=["voPersonStatus"],
        )
        for attrs in people.values():
            # Skip holding-area entry (no o= in DN)
            statuses.extend(attrs.get("voPersonStatus") or [])
        # Prefer statuses from CO-scoped entries only
        co_statuses = []
        for dn, attrs in people.items():
            if ",o=" in dn:
                co_statuses.extend(attrs.get("voPersonStatus") or [])
        status = flat.merge_vo_person_status(co_statuses or statuses or ["active"])
        entry = flat.flat_person_entry(ldap_attrs, status)
        self._upsert(dit.flat_person_dn(uid, self.ldap_basename), entry)

    # --- Groups -------------------------------------------------------------

    def _get_group(self, id: str) -> Optional[dict]:
        groups = self._search(
            dit.ordered_base(self.ldap_basename),
            f"(&(objectClass=groupOfMembers)(uniqueIdentifier={id}))",
            attributes=["*"],
        )
        if not groups:
            return None
        dn, attrs = next(iter(groups.items()))
        display = attrs.get("displayName")
        display_val = display[0] if isinstance(display, list) else display
        return {
            "id": id,
            "displayName": display_val,
            "members": [],
        }

    def _set_group(self, id: str, resource: dict) -> None:
        ext = mapping._extension(resource, mapping.sram_group_schema())
        urn = ext.get("urn")
        if not urn:
            raise ValueError(
                f"SCIM Group {id} missing {mapping.sram_group_schema()}.urn"
            )

        co_identifier, group_cn = dit.parse_group_urn(urn)
        self._ensure_co_containers(co_identifier)

        if group_cn is None or mapping.is_collaboration_group(resource):
            group_cn = "@all"
            co_attrs = mapping.scim_group_to_co_ldap(resource, co_identifier)
            self._upsert(dit.co_dn(co_identifier, self.ldap_basename), co_attrs)

        grp_attrs = mapping.scim_group_to_group_ldap(resource, group_cn)
        member_uids = self._member_uids(resource)

        # Ensure each member exists under this CO's People
        member_dns: List[str] = []
        for uid in member_uids:
            person_dn = dit.person_dn(uid, co_identifier, self.ldap_basename)
            # Copy from holding area or any existing person entry
            sources = self._search(
                dit.ordered_base(self.ldap_basename),
                f"(&(objectClass=person)(uid={uid}))",
                attributes=["*"],
            )
            if sources:
                src_attrs = next(iter(sources.values()))
                # ldap3 returns Attribute values; normalize to lists of scalars
                normalized = {
                    k: (v if isinstance(v, list) else [v])
                    for k, v in src_attrs.items()
                    if k != "dn"
                }
                if "objectClass" not in normalized:
                    normalized = mapping.scim_user_to_ldap(
                        {"userName": uid, "displayName": uid, "active": True}
                    )
                self._upsert(person_dn, normalized)
            else:
                logger.warning(
                    "No person entry for uid=%s when writing group %s", uid, id
                )
                continue
            member_dns.append(person_dn)

        grp_attrs["member"] = member_dns
        grp_dn = dit.ordered_group_dn(group_cn, co_identifier, self.ldap_basename)
        self._upsert(grp_dn, grp_attrs)

        if self.flat_derive:
            self._derive_flat_group(co_identifier, group_cn, grp_attrs, member_dns)
            for uid in member_uids:
                person = self._search(
                    dit.people_ou_dn(co_identifier, self.ldap_basename),
                    f"(uid={uid})",
                    attributes=["*"],
                )
                if person:
                    attrs = next(iter(person.values()))
                    normalized = {
                        k: (v if isinstance(v, list) else [v])
                        for k, v in attrs.items()
                    }
                    self._derive_flat_person(uid, normalized)

    def _derive_flat_group(
        self,
        co_identifier: str,
        group_cn: str,
        ordered_attrs: Dict[str, List[Any]],
        ordered_member_dns: List[str],
    ) -> None:
        flat_members = flat.rewrite_members_to_flat(
            ordered_member_dns, self.ldap_basename
        )
        entry = flat.flat_group_entry(
            ordered_attrs, co_identifier, group_cn, flat_members
        )
        self._upsert(
            dit.flat_group_dn(co_identifier, group_cn, self.ldap_basename),
            entry,
        )
