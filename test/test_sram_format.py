"""SRAM-dictated LDAP format tests (local, no LDAP required).

These encode the shapes observed on ldaps://ldap.sram.surf.nl so mapping /
flat derive cannot drift without failing CI.
"""

import base64

import pytest

from data.plugins.sram_ldap import flat, mapping, sram_format


@pytest.fixture(autouse=True)
def sram_schema(monkeypatch):
    monkeypatch.setenv("SRAM_SCIM_SCHEMA", "urn:mace:surf.nl:sram:scim:extension")


def _oc(entry):
    return sorted(x.lower() for x in entry.get("objectClass", []))


def test_sram_person_mapping_matches_dictated_ocs_and_forbids_overlays():
    schema = mapping.sram_user_schema()
    ssh = base64.b64encode(b"ssh-ed25519 AAAA test@host").decode()
    entry = mapping.scim_user_to_ldap(
        {
            "userName": "hkodden5",
            "displayName": "Harry Kodden",
            "name": {"givenName": "Harry", "familyName": "Kodden"},
            "active": True,
            "emails": [{"value": "harry.kodden@surf.nl", "primary": True}],
            "x509Certificates": [{"value": ssh}],
            "externalId": "44cb3ba1-7a58-49af-961d-9a1253a26181@sram.surf.nl",
            schema: {
                "eduPersonUniqueId": (
                    "202da8fbdc367c4996d5b3e064c9ca4d7d91110a@sram.surf.nl"
                ),
                "voPersonExternalId": "kodde001@surf.nl",
                "voPersonExternalAffiliation": "employee@surf.nl",
                "sramInactiveDays": 1,
                "voPersonPolicyAgreement": [
                    {"value": "https://sram.surf.nl/aup", "time": 1780922154},
                ],
            },
        }
    )

    # Mapping output is SRAM person shape (plugin may add uniqueIdentifier later).
    assert "uniqueIdentifier" not in entry
    assert "extensibleObject" not in entry["objectClass"]
    expected_ocs = set(sram_format.SRAM_PERSON_OBJECT_CLASSES_BASE) | {
        "ldapPublicKey"
    }
    assert set(entry["objectClass"]) == expected_ocs
    assert sram_format.SRAM_PERSON_CORE_ATTRS <= set(entry)
    assert entry["voPersonPolicyAgreement;time-1780922154"] == [
        "https://sram.surf.nl/aup"
    ]
    assert entry["eduPersonScopedAffiliation"] == ["member@sram.surf.nl"]
    assert entry["sramInactiveDays"] == ["1"]


def test_sram_person_without_ssh_has_no_ldap_public_key_oc():
    entry = mapping.scim_user_to_ldap(
        {
            "userName": "dsalek2",
            "displayName": "David",
            "name": {"givenName": "David", "familyName": "Salek"},
            "active": True,
            "emails": [{"value": "d@example.org"}],
        }
    )
    assert "ldapPublicKey" not in entry["objectClass"]
    assert set(entry["objectClass"]) == set(
        sram_format.SRAM_PERSON_OBJECT_CLASSES_BASE
    )


def test_sram_co_mapping_dictated_attrs():
    schema = mapping.sram_group_schema()
    entry = mapping.scim_group_to_co_ldap(
        {
            "id": "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58@sram.surf.nl",
            "externalId": "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58@sram.surf.nl",
            "displayName": "harry-test",
            "active": True,
            "emails": [
                {"value": "salekd@gmail.com"},
                {"value": "david.salek@surf.nl"},
                {"value": "harry.kodden@surf.nl"},
            ],
            schema: {
                "urn": "surf:harrytest",
                "description": "S3 Project harry-test",
                "links": [
                    {
                        "name": "sbs_url",
                        "value": (
                            "https://sram.surf.nl/collaborations/"
                            "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58"
                        ),
                    },
                    {
                        "name": "logo",
                        "value": (
                            "https://sram.surf.nl/api/images/collaborations/"
                            "79b24269-bd1f-4ffa-a408-28cf9128db74"
                        ),
                    },
                ],
            },
        },
        "surf.harrytest",
    )
    assert set(entry["objectClass"]) == set(sram_format.SRAM_CO_OBJECT_CLASSES)
    assert sram_format.SRAM_CO_REQUIRED_ATTRS <= set(entry)
    assert entry["uniqueIdentifier"] == [
        "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58"
    ]
    assert entry["organizationalStatus"] == ["active"]
    assert entry["mail"] == [
        "salekd@gmail.com",
        "david.salek@surf.nl",
        "harry.kodden@surf.nl",
    ]
    assert "@" not in entry["uniqueIdentifier"][0]


def test_sram_all_group_labels_dictated():
    schema = mapping.sram_group_schema()
    entry = mapping.scim_group_to_group_ldap(
        {
            "displayName": "harry-test",
            "externalId": "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58@sram.surf.nl",
            schema: {
                "urn": "surf:harrytest",
                "description": "S3 Project harry-test",
                "links": [
                    {
                        "name": "sbs_url",
                        "value": "https://sram.surf.nl/collaborations/fb9ce3da",
                    }
                ],
            },
        },
        "@all",
        co_display_name="harry-test",
    )
    assert entry["cn"] == ["@all"]
    assert entry["displayName"] == [
        sram_format.sram_all_display_name("harry-test")
    ]
    assert entry["description"] == [sram_format.SRAM_ALL_DESCRIPTION]
    assert set(entry["objectClass"]) == set(
        sram_format.SRAM_ALL_GROUP_OBJECT_CLASSES
    )
    assert entry["uniqueIdentifier"] == [
        "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58"
    ]
    # Collaboration description must NOT leak onto @all (SRAM uses fixed text).
    assert entry["description"] != ["S3 Project harry-test"]


def test_sram_admin_subgroup_dictated():
    schema = mapping.sram_group_schema()
    entry = mapping.scim_group_to_group_ldap(
        {
            "displayName": "admin",
            "externalId": "9dbc5382-8017-4bfe-b52a-f3eddf34da11@sram.surf.nl",
            schema: {
                "urn": "surf:harrytest:admin",
                "description": "Project administrator",
            },
        },
        "admin",
    )
    assert entry["cn"] == ["admin"]
    assert entry["displayName"] == ["admin"]
    assert entry["description"] == ["Project administrator"]
    assert set(entry["objectClass"]) == set(
        sram_format.SRAM_SUBGROUP_OBJECT_CLASSES
    )
    assert entry["uniqueIdentifier"] == [
        "9dbc5382-8017-4bfe-b52a-f3eddf34da11"
    ]


def test_flat_person_strips_scim_store_overlays():
    ordered = mapping.scim_user_to_ldap(
        {
            "userName": "hkodden5",
            "displayName": "Harry",
            "name": {"givenName": "Harry", "familyName": "Kodden"},
            "active": True,
        }
    )
    # Simulate plugin SCIM-store overlay
    ordered["uniqueIdentifier"] = [
        "44cb3ba1-7a58-49af-961d-9a1253a26181@sram.surf.nl"
    ]
    ordered["objectClass"] = list(ordered["objectClass"]) + ["extensibleObject"]
    flat_entry = flat.flat_person_entry(ordered, "active")
    assert "uniqueIdentifier" not in flat_entry
    assert "extensibleObject" not in flat_entry["objectClass"]
    assert flat_entry["voPersonStatus"] == ["active"]


def test_flat_group_projects_co_mail_and_status():
    ordered = mapping.scim_group_to_group_ldap(
        {
            "displayName": "harry-test",
            "externalId": "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58@sram.surf.nl",
            mapping.sram_group_schema(): {"urn": "surf:harrytest"},
        },
        "@all",
        co_display_name="harry-test",
    )
    entry = flat.flat_group_entry(
        ordered,
        "surf.harrytest",
        "@all",
        ["uid=hkodden5,ou=People,dc=flat,dc=x"],
        co_attrs={
            "mail": ["a@example.org", "b@example.org"],
            "organizationalStatus": ["active"],
        },
    )
    assert entry["cn"] == ["surf.harrytest.@all"]
    assert entry["displayName"] == [
        sram_format.sram_all_display_name("harry-test")
    ]
    assert entry["description"] == [sram_format.SRAM_ALL_DESCRIPTION]
    assert sram_format.SRAM_FLAT_GROUP_EXTRA_ATTRS <= set(entry)
    assert entry["mail"] == ["a@example.org", "b@example.org"]
    assert entry["organizationalStatus"] == ["active"]


def test_co_contact_mail_from_members_when_payload_omits_emails():
    co_attrs = {
        "objectClass": list(sram_format.SRAM_CO_OBJECT_CLASSES),
        "o": ["surf.harrytest"],
        "displayName": ["harry-test"],
    }
    assert mapping.co_contact_mail_from_members(co_attrs, []) is None
    assert mapping.co_contact_mail_from_members(
        co_attrs,
        ["harry.kodden@surf.nl", "david.salek@surf.nl", "harry.kodden@surf.nl"],
    ) == ["harry.kodden@surf.nl", "david.salek@surf.nl"]
    co_attrs["mail"] = ["from-payload@surf.nl"]
    assert mapping.co_contact_mail_from_members(
        co_attrs, ["member@surf.nl"]
    ) is None


def test_flat_subgroup_also_gets_co_extras():
    ordered = mapping.scim_group_to_group_ldap(
        {
            "displayName": "admin",
            "externalId": "9dbc5382-8017-4bfe-b52a-f3eddf34da11@sram.surf.nl",
            mapping.sram_group_schema(): {
                "urn": "surf:harrytest:admin",
                "description": "Project administrator",
            },
        },
        "admin",
    )
    entry = flat.flat_group_entry(
        ordered,
        "surf.harrytest",
        "admin",
        ["uid=hkodden5,ou=People,dc=flat,dc=x"],
        co_attrs={
            "mail": ["harry.kodden@surf.nl"],
            "organizationalStatus": ["active"],
        },
    )
    assert entry["cn"] == ["surf.harrytest.admin"]
    assert entry["mail"] == ["harry.kodden@surf.nl"]
    assert entry["organizationalStatus"] == ["active"]
