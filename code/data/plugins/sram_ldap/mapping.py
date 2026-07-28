"""Map SBS/SRAM SCIM payloads to LDAP attribute dicts (PLSC-compatible)."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional

DEFAULT_SRAM_SCHEMA = "urn:mace:surf.nl:sram:scim:extension"


def sram_schema_base() -> str:
    return os.environ.get("SRAM_SCIM_SCHEMA", DEFAULT_SRAM_SCHEMA)


def sram_user_schema() -> str:
    return f"{sram_schema_base()}:User"


def sram_group_schema() -> str:
    return f"{sram_schema_base()}:Group"


def _extension(resource: dict, schema: str) -> dict:
    ext = resource.get(schema)
    return ext if isinstance(ext, dict) else {}


def _primary_email(resource: dict) -> Optional[str]:
    for email in resource.get("emails") or []:
        if email.get("primary"):
            return email.get("value")
    emails = resource.get("emails") or []
    if emails:
        return emails[0].get("value")
    return None


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

    record: Dict[str, List[Any]] = {
        "objectClass": [
            "inetOrgPerson",
            "person",
            "eduPerson",
            "voPerson",
            "sramPerson",
        ],
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
        record["objectClass"].append("ldapPublicKey")
        record["sshPublicKey"] = ssh_keys

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
        "objectClass": ["top", "organization", "extensibleObject"],
        "o": [co_identifier],
    }
    external_id = resource.get("externalId") or resource.get("id")
    if external_id:
        entry["uniqueIdentifier"] = [external_id]
    if resource.get("displayName"):
        entry["displayName"] = [resource["displayName"]]
    if ext.get("description"):
        entry["description"] = [ext["description"]]
    if ext.get("labels"):
        entry["businessCategory"] = list(ext["labels"])

    labeled: List[str] = []
    for link in ext.get("links") or []:
        name = link.get("name")
        value = link.get("value")
        if name and value:
            labeled.append(f"{value.strip().replace(' ', '%20')} {name}")
    if labeled:
        entry["labeledURI"] = labeled

    return entry


def scim_group_to_group_ldap(
    resource: dict, group_cn: str
) -> Dict[str, List[Any]]:
    """Build groupOfMembers attributes (members filled by caller)."""
    ext = _extension(resource, sram_group_schema())
    entry: Dict[str, List[Any]] = {
        "objectClass": ["extensibleObject", "groupOfMembers"],
        "cn": [group_cn],
        "member": [],
    }
    external_id = resource.get("externalId") or resource.get("id")
    if external_id:
        entry["uniqueIdentifier"] = [external_id]
    if resource.get("displayName"):
        entry["displayName"] = [resource["displayName"]]
    if ext.get("description"):
        entry["description"] = [ext["description"]]
    return entry
