"""Map SBS/SRAM SCIM payloads to LDAP attribute dicts (PLSC-compatible)."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional

DEFAULT_SRAM_SCHEMA = "urn:mace:surf.nl:sram:scim:extension"
VOPERSON_SCHEMA = "urn:temporaryNamespace:scim:schemas:voPerson:User"


from data.plugins.sram_ldap import sram_format


def sram_schema_base() -> str:
    return os.environ.get("SRAM_SCIM_SCHEMA", DEFAULT_SRAM_SCHEMA)



def sram_user_schema() -> str:
    return f"{sram_schema_base()}:User"


def sram_group_schema() -> str:
    return f"{sram_schema_base()}:Group"


def _extension(resource: dict, schema: str) -> dict:
    ext = resource.get(schema)
    return ext if isinstance(ext, dict) else {}


def bare_unique_identifier(value: Optional[str]) -> Optional[str]:
    """SRAM CO uniqueIdentifier is a bare UUID (no @realm suffix)."""
    if not value:
        return None
    return value.split("@", 1)[0]


def scim_store_identifiers(
    scim_id: str, external_id: Optional[str] = None
) -> List[str]:
    """LDAP uniqueIdentifier values for the SCIM store overlay.

    First value is the server-generated SCIM ``id``. Extra values are the
    client ``externalId`` (and its bare UUID form) so Group ``members.value``
    can resolve whether the client sends the server id or its own id.
    """
    values: List[str] = []
    if scim_id:
        values.append(str(scim_id))
    if external_id:
        ext = str(external_id)
        bare = bare_unique_identifier(ext) or ext
        for candidate in (ext, bare):
            if candidate and candidate not in values:
                values.append(candidate)
    return values


def split_scim_store_identifiers(
    values: Optional[List[Any]],
) -> tuple[Optional[str], Optional[str]]:
    """Return (canonical_scim_id, external_id) from stored uniqueIdentifier."""
    if not values:
        return None, None
    if not isinstance(values, list):
        values = [values]
    cleaned = [str(v) for v in values if v is not None and str(v) != ""]
    if not cleaned:
        return None, None
    scim_id = cleaned[0]
    external_id = cleaned[1] if len(cleaned) > 1 else cleaned[0]
    return scim_id, external_id


def _primary_email(resource: dict) -> Optional[str]:
    for email in resource.get("emails") or []:
        if email.get("primary"):
            return email.get("value")
    emails = resource.get("emails") or []
    if emails:
        return emails[0].get("value")
    return None


def _all_emails(resource: dict) -> List[str]:
    values: List[str] = []
    for email in resource.get("emails") or []:
        value = email.get("value") if isinstance(email, dict) else email
        if value and value not in values:
            values.append(value)
    return values


def _ssh_keys(resource: dict) -> List[str]:
    keys: List[str] = []
    for item in resource.get("x509Certificates") or []:
        value = item.get("value")
        if not value:
            continue
        try:
            keys.append(base64.b64decode(value).decode("utf-8"))
        except Exception:
            # Already plain OpenSSH key material
            keys.append(value)
    return keys


def _labeled_uris(ext: dict) -> List[str]:
    labeled: List[str] = []
    for link in ext.get("links") or []:
        name = link.get("name")
        value = link.get("value")
        if name and value:
            labeled.append(f"{value.strip().replace(' ', '%20')} {name}")
    return labeled


def _policy_agreement_attrs(resource: dict) -> Dict[str, List[Any]]:
    """Map voPersonPolicyAgreement → LDAP option attrs ``;time-<epoch>``."""
    out: Dict[str, List[Any]] = {}
    for schema in (VOPERSON_SCHEMA, sram_user_schema()):
        ext = _extension(resource, schema)
        agreements = ext.get("voPersonPolicyAgreement") or []
        if isinstance(agreements, dict):
            agreements = [agreements]
        for item in agreements:
            if not isinstance(item, dict):
                continue
            url = item.get("value")
            if not url:
                continue
            time = item.get("time")
            if time is None:
                out.setdefault("voPersonPolicyAgreement", []).append(url)
            else:
                key = f"voPersonPolicyAgreement;time-{time}"
                out.setdefault(key, []).append(url)
    return out


def scim_user_to_ldap(resource: dict) -> Dict[str, List[Any]]:
    """Build ordered-tree person attributes from a SCIM User resource."""
    ext = _extension(resource, sram_user_schema())
    name = resource.get("name") or {}
    uid = resource.get("userName")
    if not uid:
        raise ValueError("SCIM User requires userName (LDAP uid)")

    edu_unique = ext.get("eduPersonUniqueId") or resource.get("externalId") or uid
    display = resource.get("displayName") or "n/a"
    given = name.get("givenName") or "n/a"
    family = name.get("familyName") or "n/a"
    mail = _primary_email(resource)

    active = resource.get("active", True)
    status = "active" if active else "expired"

    # Match SRAM person objectClass set (no extensibleObject).
    record: Dict[str, List[Any]] = {
        "objectClass": list(sram_format.SRAM_PERSON_OBJECT_CLASSES_BASE),
        "uid": [uid],
        "cn": [edu_unique],
        "eduPersonUniqueId": [edu_unique],
        "displayName": [display],
        "givenName": [given],
        "sn": [family],
        "voPersonStatus": [status],
        "eduPersonScopedAffiliation": ["member@sram.surf.nl"],
    }

    if mail:
        record["mail"] = [mail]

    if ext.get("voPersonExternalAffiliation"):
        affiliations = ext["voPersonExternalAffiliation"]
        if isinstance(affiliations, str):
            affiliations = [a.strip() for a in affiliations.split(",") if a.strip()]
        record["voPersonExternalAffiliation"] = list(affiliations)

    if ext.get("voPersonExternalId"):
        record["voPersonExternalID"] = [ext["voPersonExternalId"]]

    if ext.get("eduPersonScopedAffiliation"):
        record["eduPersonScopedAffiliation"] = [ext["eduPersonScopedAffiliation"]]

    if ext.get("sramInactiveDays") is not None:
        record["sramInactiveDays"] = [str(ext["sramInactiveDays"])]

    ssh_keys = _ssh_keys(resource)
    if ssh_keys:
        # Requires openssh-lpk schema (sshPublicKey + ldapPublicKey).
        if "ldapPublicKey" not in record["objectClass"]:
            record["objectClass"].append("ldapPublicKey")
        record["sshPublicKey"] = ssh_keys

    record.update(_policy_agreement_attrs(resource))

    return record


def is_collaboration_group(resource: dict) -> bool:
    """True when the SCIM Group represents a Collaboration (CO), not a subgroup."""
    ext = _extension(resource, sram_group_schema())
    links = ext.get("links") or []
    if any(link.get("name") == "sbs_url" for link in links):
        return True
    urn = ext.get("urn") or ""
    from data.plugins.sram_ldap.dit import parse_group_urn
    _, group_cn = parse_group_urn(urn) if urn else ("", None)
    return group_cn is None


def scim_group_to_co_ldap(resource: dict, co_identifier: str) -> Dict[str, List[Any]]:
    """Build organization entry attributes for a Collaboration."""
    ext = _extension(resource, sram_group_schema())
    entry: Dict[str, List[Any]] = {
        "objectClass": list(sram_format.SRAM_CO_OBJECT_CLASSES),
        "o": [co_identifier],
    }
    external_id = bare_unique_identifier(
        resource.get("externalId") or resource.get("id")
    )
    if external_id:
        entry["uniqueIdentifier"] = [external_id]
    if resource.get("displayName"):
        entry["displayName"] = [resource["displayName"]]
    else:
        entry["displayName"] = [co_identifier.split(".")[-1]]
    description = ext.get("description") or resource.get("description")
    if description:
        entry["description"] = [description]
    if ext.get("labels"):
        entry["businessCategory"] = list(ext["labels"])

    labeled = _labeled_uris(ext)
    if labeled:
        entry["labeledURI"] = labeled

    # Contact mails: core emails[] and/or extension mail/emails (SBS may send either).
    mails = _all_emails(resource)
    for key in ("mail", "emails"):
        raw = ext.get(key)
        if isinstance(raw, str):
            if raw not in mails:
                mails.append(raw)
        elif isinstance(raw, list):
            for item in raw:
                value = item.get("value") if isinstance(item, dict) else item
                if value and value not in mails:
                    mails.append(value)
    if mails:
        entry["mail"] = mails

    # SRAM organizationalStatus: active | … — derive from SCIM active when present.
    status = ext.get("organizationalStatus")
    if status:
        entry["organizationalStatus"] = [status]
    elif "active" in resource:
        entry["organizationalStatus"] = [
            "active" if resource.get("active") else "expired"
        ]
    else:
        entry["organizationalStatus"] = ["active"]

    return entry


def scim_group_to_group_ldap(
    resource: dict,
    group_cn: str,
    *,
    co_display_name: Optional[str] = None,
) -> Dict[str, List[Any]]:
    """Build groupOfMembers attributes (members filled by caller).

    For ``cn=@all``, use SRAM labels from ``sram_format``.
    """
    ext = _extension(resource, sram_group_schema())
    entry: Dict[str, List[Any]] = {
        "objectClass": list(sram_format.SRAM_ALL_GROUP_OBJECT_CLASSES),
        "cn": [group_cn],
    }
    # SRAM stores bare UUID (no @realm) on group uniqueIdentifier.
    external_id = bare_unique_identifier(
        resource.get("externalId") or resource.get("id")
    )
    if external_id:
        entry["uniqueIdentifier"] = [external_id]

    if group_cn == "@all":
        label = (
            co_display_name
            or resource.get("displayName")
            or "Collaboration"
        )
        entry["displayName"] = [sram_format.sram_all_display_name(label)]
        entry["description"] = [sram_format.SRAM_ALL_DESCRIPTION]
    else:
        entry["objectClass"] = list(sram_format.SRAM_SUBGROUP_OBJECT_CLASSES)
        if resource.get("displayName"):
            entry["displayName"] = [resource["displayName"]]
        description = ext.get("description") or resource.get("description")
        if description:
            entry["description"] = [description]

    labeled = _labeled_uris(ext)
    if labeled:
        entry["labeledURI"] = labeled
    return entry
