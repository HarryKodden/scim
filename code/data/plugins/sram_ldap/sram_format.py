"""SRAM service LDAP shapes that SCIM must produce (dictated format).

Captured from ldaps://ldap.sram.surf.nl (service tree) 2026-07-29.
Values that vary per deployment (SSH key material, absolute member DNs, UUIDs)
are represented by placeholders or structural assertions in tests — not copied
verbatim when they are not format-relevant.
"""

from __future__ import annotations

# Collaboration organization (o=<org.co>,dc=ordered,…)
SRAM_CO_OBJECT_CLASSES = ["top", "organization", "extensibleObject"]
SRAM_CO_REQUIRED_ATTRS = {
    "o",
    "objectClass",
    "displayName",
    "description",
    "organizationalStatus",
    "uniqueIdentifier",  # bare UUID, no @realm
    "labeledURI",
    "mail",
}

# cn=@all under a CO
SRAM_ALL_GROUP_OBJECT_CLASSES = ["extensibleObject", "groupOfMembers"]
SRAM_ALL_DESCRIPTION = "All CO members"


def sram_all_display_name(co_display_name: str) -> str:
    return f"All Members of {co_display_name}"


# Subgroup (e.g. cn=admin)
SRAM_SUBGROUP_OBJECT_CLASSES = ["extensibleObject", "groupOfMembers"]

# Person under ou=People,o=<co>,dc=ordered (and flat People)
# Note: SRAM does NOT place uniqueIdentifier or extensibleObject on persons.
SRAM_PERSON_OBJECT_CLASSES_BASE = [
    "inetOrgPerson",
    "person",
    "eduPerson",
    "voPerson",
    "sramPerson",
]
# + ldapPublicKey when sshPublicKey is present

SRAM_PERSON_FORBIDDEN_ATTRS = {
    "uniqueIdentifier",  # SCIM store may overlay this on ordered only; not in SRAM
    "extensibleObject",  # must not appear in objectClass
}

SRAM_PERSON_CORE_ATTRS = {
    "uid",
    "cn",
    "eduPersonUniqueId",
    "displayName",
    "givenName",
    "sn",
    "mail",
    "voPersonStatus",
    "eduPersonScopedAffiliation",
    "objectClass",
}

# Flat group cn=<co>.<group> projects CO mail + organizationalStatus
SRAM_FLAT_GROUP_EXTRA_ATTRS = {"mail", "organizationalStatus"}
