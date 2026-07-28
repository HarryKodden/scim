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

    SBS ``global_urn`` forms (preferred)::

        org:co           → ("org.co", None)          # collaboration → cn=@all
        org:co:group     → ("org.co", "group")       # subgroup
        org:co:a:b       → ("org.co", "a.b")

    Also accepted (fixtures / legacy)::

        org.co           → ("org.co", None)
        org.co:group     → ("org.co", "group")       # dotted CO + colon group
        org.co.group     → ("org.co", "group")       # all dots (last segment = group)

    Important: do **not** treat only the first colon segment as the CO.
    ``surf:demo1:admin`` must become ``o=surf.demo1`` + ``cn=admin``, not
    ``o=surf`` + ``cn=demo1.admin`` (SRAM service LDAP layout).
    """
    if not urn:
        raise ValueError("group urn is required")

    urn = urn.strip()
    if ":" in urn:
        parts = [p for p in urn.split(":") if p]
        if len(parts) >= 3:
            # org:co:group[:…]
            return f"{parts[0]}.{parts[1]}", ".".join(parts[2:])
        if len(parts) == 2:
            left, right = parts
            if "." in left:
                # org.co:group (dotted CO already)
                return left, right
            # org:co collaboration
            return f"{left}.{right}", None
        return parts[0], None

    parts = urn.split(".")
    if len(parts) <= 2:
        return urn, None
    return ".".join(parts[:-1]), parts[-1]
