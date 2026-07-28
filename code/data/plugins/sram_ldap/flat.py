"""Derive the flat SRAM LDAP subtree from ordered entries."""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional

from data.plugins.sram_ldap import dit

logger = logging.getLogger(__name__)


def merge_vo_person_status(statuses: List[str]) -> str:
    """Flat-tree rule: active if active in any collaboration."""
    if any(s == "active" for s in statuses):
        return "active"
    return statuses[-1] if statuses else "expired"


def flat_person_entry(ordered_entry: Dict[str, List[Any]], status: str) -> Dict[str, List[Any]]:
    entry = copy.deepcopy(ordered_entry)
    entry["voPersonStatus"] = [status]
    return entry


def flat_group_entry(
    ordered_entry: Dict[str, List[Any]],
    co_identifier: str,
    group_cn: str,
    flat_member_dns: List[str],
    *,
    co_attrs: Optional[Dict[str, List[Any]]] = None,
) -> Dict[str, List[Any]]:
    entry = copy.deepcopy(ordered_entry)
    entry["cn"] = [f"{co_identifier}.{group_cn}"]
    entry["member"] = list(flat_member_dns)
    # SRAM projects CO mail + organizationalStatus onto flat groups.
    if co_attrs:
        if co_attrs.get("mail") and not entry.get("mail"):
            entry["mail"] = list(co_attrs["mail"])
        status = co_attrs.get("organizationalStatus")
        if status:
            entry["organizationalStatus"] = list(status)
        elif "organizationalStatus" not in entry:
            entry["organizationalStatus"] = ["active"]
    elif "organizationalStatus" not in entry:
        entry["organizationalStatus"] = ["active"]
    return entry


def rewrite_members_to_flat(
    ordered_member_dns: List[str], ldap_basename: str
) -> List[str]:
    """Map ordered People DNs to flat People DNs (by uid RDN)."""
    result = []
    for member_dn in ordered_member_dns:
        # uid=<uid>,ou=People,o=...,dc=ordered,...
        rdn = member_dn.split(",", 1)[0]
        if not rdn.lower().startswith("uid="):
            logger.warning("Skipping non-uid member DN in flat rewrite: %s", member_dn)
            continue
        uid = rdn.split("=", 1)[1]
        result.append(dit.flat_person_dn(uid, ldap_basename))
    return result
