"""DN and DIT helpers for the SRAM ordered / flat LDAP trees."""

from __future__ import annotations

from typing import Optional, Tuple


def ordered_base(ldap_basename: str) -> str:
    return f"dc=ordered,{ldap_basename}"


def flat_base(ldap_basename: str) -> str:
    return f"dc=flat,{ldap_basename}"


def co_dn(co_identifier: str, ldap_basename: str) -> str:
    return f"o={co_identifier},{ordered_base(ldap_basename)}"


def people_ou_dn(co_identifier: str, ldap_basename: str) -> str:
    return f"ou=People,{co_dn(co_identifier, ldap_basename)}"


def groups_ou_dn(co_identifier: str, ldap_basename: str) -> str:
    return f"ou=Groups,{co_dn(co_identifier, ldap_basename)}"


def person_dn(uid: str, co_identifier: str, ldap_basename: str) -> str:
    return f"uid={uid},{people_ou_dn(co_identifier, ldap_basename)}"


def ordered_group_dn(
    group_cn: str, co_identifier: str, ldap_basename: str
) -> str:
    return f"cn={group_cn},{groups_ou_dn(co_identifier, ldap_basename)}"


def flat_people_ou_dn(ldap_basename: str) -> str:
    return f"ou=People,{flat_base(ldap_basename)}"


def flat_groups_ou_dn(ldap_basename: str) -> str:
    return f"ou=Groups,{flat_base(ldap_basename)}"


def flat_person_dn(uid: str, ldap_basename: str) -> str:
    return f"uid={uid},{flat_people_ou_dn(ldap_basename)}"


def flat_group_dn(co_identifier: str, group_cn: str, ldap_basename: str) -> str:
    return (
        f"cn={co_identifier}.{group_cn},"
        f"{flat_groups_ou_dn(ldap_basename)}"
    )


def parse_group_urn(urn: str) -> Tuple[str, Optional[str]]:
    """Split an SRAM group urn into (co_identifier, group_cn|None).

    Collaboration (@all): ``org.co`` → ``("org.co", None)``
    Subgroup: ``org.co:group`` or ``org.co.group`` → ``("org.co", "group")``

    Colon form is preferred (SBS ``global_urn``). Dot form assumes the last
    segment is the group short name when more than two segments exist.
    """
    if not urn:
        raise ValueError("group urn is required")

    urn = urn.strip()
    if ":" in urn:
        co, _, group = urn.partition(":")
        group = group.replace(":", ".")
        return co, group or None

    parts = urn.split(".")
    if len(parts) <= 2:
        return urn, None
    return ".".join(parts[:-1]), parts[-1]
