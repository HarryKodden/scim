"""SCIM plugin that persists Users/Groups into the SRAM LDAP directory."""

from __future__ import annotations

import json
import logging
import os
import uuid
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


def _unique_id_filter(attr: str, scim_id: str) -> str:
    """Match LDAP uniqueIdentifier as bare UUID or SCIM id with @realm."""
    bare = mapping.bare_unique_identifier(scim_id) or scim_id
    if bare == scim_id:
        return f"({attr}={scim_id})"
    return f"(|({attr}={scim_id})({attr}={bare}))"


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

        # LDAP_HOSTNAME may be a host or URI (ldap://host:1389).
        # Optional LDAP_PORT when hostname has no scheme (default 389).
        if "://" in (ldap_hostname or ""):
            server = Server(ldap_hostname, get_info=ALL)
        else:
            port = int(os.environ.get("LDAP_PORT", "389"))
            server = Server(ldap_hostname, port=port, get_info=ALL)
        self.session = Connection(
            server,
            user=ldap_username,
            password=ldap_password,
            auto_bind=True,
        )
        logger.info("SRAM LDAP connected (%s)", self.description)
        self._ensure_roots()

    def id(self, details: dict) -> str:
        """Prefer SBS externalId so Group members.value resolve after User create."""
        external = details.get("externalId") if isinstance(details, dict) else None
        if external:
            return str(external)
        return str(uuid.uuid4())

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
        # Minimal org body (collaboration upsert enriches displayName/links/mail).
        short = co_identifier.split(".")[-1] if co_identifier else co_identifier
        if not self.session.search(co_dn, "(objectClass=*)", search_scope="BASE"):
            self._ensure_entry(
                co_dn,
                {
                    "objectClass": ["top", "organization", "extensibleObject"],
                    "o": [co_identifier],
                    "displayName": [short],
                    "organizationalStatus": ["active"],
                },
            )
        for ou in ("People", "Groups"):
            self._ensure_entry(
                f"ou={ou},{co_dn}",
                {"objectClass": ["top", "organizationalUnit"], "ou": [ou]},
            )
        # SRAM always has cn=@all under each CO; create a stub if missing so the
        # DIT matches before the collaboration SCIM resource arrives.
        all_dn = dit.ordered_group_dn("@all", co_identifier, self.ldap_basename)
        self._ensure_entry(
            all_dn,
            {
                "objectClass": ["extensibleObject", "groupOfMembers"],
                "cn": ["@all"],
                "displayName": ["@all"],
            },
        )

    def _sanitize_attributes(
        self, attributes: Dict[str, List[Any]]
    ) -> Dict[str, List[Any]]:
        """Drop empty values — OpenLDAP rejects attributes with no values."""
        clean: Dict[str, List[Any]] = {}
        for attr, values in attributes.items():
            if values is None:
                continue
            if isinstance(values, list) and len(values) == 0:
                continue
            clean[attr] = values
        return clean

    def _upsert(self, dn: str, attributes: Dict[str, List[Any]]) -> None:
        attributes = self._sanitize_attributes(attributes)
        is_group = any(
            str(oc).lower() == "groupofmembers"
            for oc in (attributes.get("objectClass") or [])
        )
        if self.session.search(dn, "(objectClass=*)", search_scope="BASE", attributes=["*"]):
            changes = {}
            for attr, values in attributes.items():
                if attr.lower() == "objectclass":
                    continue
                changes[attr] = [("MODIFY_REPLACE", values)]
            if "objectClass" in attributes:
                changes["objectClass"] = [
                    ("MODIFY_REPLACE", attributes["objectClass"])
                ]
            # Only clear member on groupOfMembers entries (never on organization).
            if is_group and "member" not in attributes:
                changes["member"] = [("MODIFY_DELETE", [])]
            ok = self.session.modify(dn, changes)
            # MODIFY_DELETE on missing member is fine to ignore
            if not ok and self.session.result.get("description") == "noSuchAttribute":
                changes.pop("member", None)
                ok = self.session.modify(dn, changes) if changes else True
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
            f"(&(objectClass=person)(|(uniqueIdentifier={user_id})"
            f"(eduPersonUniqueId={user_id})(cn={user_id})))",
            attributes=["uid", "eduPersonUniqueId", "cn", "displayName",
                        "uniqueIdentifier"],
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
                attributes=["uniqueIdentifier", "eduPersonUniqueId", "cn"],
            )
            for attrs in people.values():
                key = attrs.get("uniqueIdentifier") or attrs.get(
                    "eduPersonUniqueId"
                ) or attrs.get("cn")
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
                    yield dn

    def __delitem__(self, id: str) -> None:
        if self.resource_type == self.USERS:
            people = self._search(
                dit.ordered_base(self.ldap_basename),
                f"(&(objectClass=person)(|(uniqueIdentifier={id})"
                f"(eduPersonUniqueId={id})(cn={id})))",
            )
            for dn in people:
                self.session.delete(dn)
            if self.flat_derive:
                flat_people = self._search(
                    dit.flat_base(self.ldap_basename),
                    f"(&(objectClass=person)(|(uniqueIdentifier={id})"
                    f"(eduPersonUniqueId={id})(cn={id})))",
                )
                for dn in flat_people:
                    self.session.delete(dn)
            return

        id_filter = _unique_id_filter("uniqueIdentifier", id)
        groups = self._search(
            dit.ordered_base(self.ldap_basename),
            f"(&(objectClass=groupOfMembers){id_filter})",
        )
        for dn in groups:
            self.session.delete(dn)
        if self.flat_derive:
            flat_groups = self._search(
                dit.flat_base(self.ldap_basename),
                f"(&(objectClass=groupOfMembers){id_filter})",
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
            f"(&(objectClass=person)(|(uniqueIdentifier={id})"
            f"(eduPersonUniqueId={id})(cn={id})))",
            attributes=["*"],
        )
        if not people:
            return None
        attrs = next(iter(people.values()))

        def first(name, default=None):
            val = attrs.get(name, default)
            if isinstance(val, list):
                return val[0] if val else default
            return val

        uid_val = first("uid")
        mail_val = first("mail")
        display_val = first("displayName")
        given = first("givenName")
        family = first("sn")
        edu_unique = first("eduPersonUniqueId")
        status = first("voPersonStatus", "active")
        scim_id = first("uniqueIdentifier") or id

        resource = {
            "id": scim_id,
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:User",
                mapping.sram_user_schema(),
            ],
            "userName": uid_val,
            "displayName": display_val,
            "externalId": scim_id,
            "active": status == "active",
            "name": {
                "givenName": given,
                "familyName": family,
            },
            "emails": (
                [{"value": mail_val, "primary": True}] if mail_val else []
            ),
            "meta": {
                "resourceType": "User",
                "location": f"/Users/{scim_id}",
            },
            mapping.sram_user_schema(): {
                "eduPersonUniqueId": edu_unique,
                "voPersonExternalId": first("voPersonExternalID"),
                "voPersonExternalAffiliation": first(
                    "voPersonExternalAffiliation"
                ),
                "sramInactiveDays": first("sramInactiveDays"),
            },
        }
        return resource

    def _set_user(self, id: str, resource: dict) -> None:
        ldap_attrs = mapping.scim_user_to_ldap(resource)
        # Persist SCIM id for round-trip GET after create
        ldap_attrs["uniqueIdentifier"] = [id]
        uid = ldap_attrs["uid"][0]

        # Refresh under every CO where this uid already exists; if none, stash
        # under no CO until a group membership write places the person.
        existing = self._search(
            dit.ordered_base(self.ldap_basename),
            f"(&(objectClass=person)(uid={uid}))",
        )
        hold_ou = f"ou=People,{dit.ordered_base(self.ldap_basename)}"
        hold_dn = f"uid={uid},{hold_ou}"

        if not existing:
            logger.info(
                "User %s (%s) stored in holding OU until CO membership",
                id,
                uid,
            )
            # Transient cache so group membership can resolve userName by SCIM id.
            self._ensure_entry(
                hold_ou,
                {"objectClass": ["top", "organizationalUnit"], "ou": ["People"]},
            )
            self._upsert(hold_dn, ldap_attrs)
            return

        for dn in existing:
            self._upsert(dn, ldap_attrs)

        # Once under any Collaboration People OU, drop the holding copy.
        if any(",o=" in dn for dn in existing):
            self._delete_if_exists(hold_dn)

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
            f"(&(objectClass=groupOfMembers)"
            f"{_unique_id_filter('uniqueIdentifier', id)})",
            attributes=["*"],
        )
        if not groups:
            return None
        dn, attrs = next(iter(groups.items()))

        def first(name, default=None):
            val = attrs.get(name, default)
            if isinstance(val, list):
                return val[0] if val else default
            return val

        # cn=@all,ou=Groups,o=org.co,dc=ordered,...
        # cn=admins,ou=Groups,o=org.co,...
        cn = first("cn")
        co_identifier = None
        for part in dn.split(","):
            if part.startswith("o="):
                co_identifier = part[2:]
                break
        urn = co_identifier
        if co_identifier and cn and cn != "@all":
            urn = f"{co_identifier}:{cn}"

        members = []
        for member_dn in attrs.get("member") or []:
            # uid=...,ou=People,...
            rdn = member_dn.split(",", 1)[0]
            if rdn.lower().startswith("uid="):
                members.append({"value": rdn.split("=", 1)[1], "display": rdn})

        return {
            "id": id,
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:Group",
                mapping.sram_group_schema(),
            ],
            "displayName": first("displayName"),
            "externalId": id,
            "members": members,
            "meta": {
                "resourceType": "Group",
                "location": f"/Groups/{id}",
            },
            mapping.sram_group_schema(): {
                "urn": urn,
                "description": first("description"),
            },
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
        # Prefer bare UUID in LDAP (SRAM parity); still accept @realm SCIM ids.
        grp_attrs["uniqueIdentifier"] = [
            mapping.bare_unique_identifier(id) or id
        ]
        member_uids = self._member_uids(resource)

        # Ensure each member exists under this CO's People
        hold_base = dit.ordered_base(self.ldap_basename)
        member_dns: List[str] = []
        for uid in member_uids:
            person_dn = dit.person_dn(uid, co_identifier, self.ldap_basename)
            hold_dn = f"uid={uid},ou=People,{hold_base}"
            # Copy from holding area or any existing person entry
            sources = self._search(
                hold_base,
                f"(&(objectClass=person)(uid={uid}))",
                attributes=["*"],
            )
            if sources:
                # Prefer an existing CO-scoped copy over the holding OU.
                src_attrs = None
                for src_dn, attrs in sources.items():
                    if ",o=" in src_dn:
                        src_attrs = attrs
                        break
                if src_attrs is None:
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
                # SRAM has no holding OU — remove after placing under the CO.
                if person_dn.lower() != hold_dn.lower():
                    self._delete_if_exists(hold_dn)
            else:
                logger.warning(
                    "No person entry for uid=%s when writing group %s", uid, id
                )
                continue
            member_dns.append(person_dn)

        if member_dns:
            grp_attrs["member"] = member_dns
        else:
            grp_attrs.pop("member", None)
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
