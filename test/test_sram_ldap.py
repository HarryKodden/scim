"""Unit tests for SRAM LDAP mapping and DIT helpers (no LDAP required)."""

import base64
import os

import pytest

from data.plugins.sram_ldap import dit, flat, mapping


@pytest.fixture(autouse=True)
def sram_schema(monkeypatch):
    monkeypatch.setenv("SRAM_SCIM_SCHEMA", "urn:mace:surf.nl:sram:scim:extension")


def test_parse_group_urn_collaboration():
    co, group = dit.parse_group_urn("org1.co1")
    assert co == "org1.co1"
    assert group is None


def test_parse_group_urn_sbs_collaboration_colon():
    """SBS global_urn for a CO is org:co (two colon segments)."""
    co, group = dit.parse_group_urn("surf:demo1")
    assert co == "surf.demo1"
    assert group is None


def test_parse_group_urn_sbs_subgroup_colon():
    """SBS subgroup urn org:co:group must not become o=org + cn=co.group."""
    co, group = dit.parse_group_urn("surf:demo1:admin")
    assert co == "surf.demo1"
    assert group == "admin"


def test_parse_group_urn_subgroup_colon():
    co, group = dit.parse_group_urn("org1.co1:admins")
    assert co == "org1.co1"
    assert group == "admins"


def test_parse_group_urn_subgroup_dot():
    co, group = dit.parse_group_urn("org1.co1.admins")
    assert co == "org1.co1"
    assert group == "admins"


def test_dit_dns():
    base = "dc=svc,dc=services,dc=example,dc=org"
    assert dit.ordered_base(base) == f"dc=ordered,{base}"
    assert dit.person_dn("alice", "org1.co1", base) == (
        f"uid=alice,ou=People,o=org1.co1,dc=ordered,{base}"
    )
    assert dit.flat_group_dn("org1.co1", "@all", base) == (
        f"cn=org1.co1.@all,ou=Groups,dc=flat,{base}"
    )


def test_scim_user_to_ldap():
    schema = mapping.sram_user_schema()
    ssh = base64.b64encode(b"ssh-ed25519 AAAA test@host").decode()
    resource = {
        "userName": "laurapage12",
        "displayName": "Laura Page",
        "name": {"givenName": "Laura", "familyName": "Page"},
        "active": True,
        "emails": [{"value": "laura@example.org", "primary": True}],
        "x509Certificates": [{"value": ssh}],
        "externalId": "47c1@sram.eduteams.org",
        schema: {
            "eduPersonUniqueId": "47c1@sram.eduteams.org",
            "voPersonExternalId": "lpage@uni.example",
            "voPersonExternalAffiliation": "employee@uni.example",
            "sramInactiveDays": 7,
            "voPersonPolicyAgreement": [
                {"value": "https://surf.nl", "time": 1780989003},
            ],
        },
    }
    entry = mapping.scim_user_to_ldap(resource)
    assert entry["uid"] == ["laurapage12"]
    assert entry["eduPersonUniqueId"] == ["47c1@sram.eduteams.org"]
    assert entry["mail"] == ["laura@example.org"]
    assert entry["voPersonStatus"] == ["active"]
    assert "ldapPublicKey" in entry["objectClass"]
    assert "extensibleObject" not in entry["objectClass"]
    assert entry["sshPublicKey"] == ["ssh-ed25519 AAAA test@host"]
    assert entry["voPersonPolicyAgreement;time-1780989003"] == ["https://surf.nl"]


def test_scim_user_inactive():
    entry = mapping.scim_user_to_ldap(
        {"userName": "bob", "displayName": "Bob", "active": False}
    )
    assert entry["voPersonStatus"] == ["expired"]


def test_scim_group_to_co_ldap_sram_parity():
    schema = mapping.sram_group_schema()
    resource = {
        "id": "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58@sram.surf.nl",
        "externalId": "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58@sram.surf.nl",
        "displayName": "harry-test",
        "active": True,
        "emails": [
            {"value": "a@example.org"},
            {"value": "b@example.org"},
        ],
        schema: {
            "urn": "surf:harrytest",
            "description": "S3 Project harry-test",
            "links": [
                {
                    "name": "sbs_url",
                    "value": "https://sram.surf.nl/collaborations/fb9ce3da",
                },
            ],
        },
    }
    entry = mapping.scim_group_to_co_ldap(resource, "surf.harrytest")
    assert entry["o"] == ["surf.harrytest"]
    assert entry["uniqueIdentifier"] == [
        "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58"
    ]
    assert entry["organizationalStatus"] == ["active"]
    assert entry["mail"] == ["a@example.org", "b@example.org"]
    assert any(u.endswith(" sbs_url") for u in entry["labeledURI"])


def test_scim_group_to_all_ldap_sram_labels():
    schema = mapping.sram_group_schema()
    resource = {
        "displayName": "harry-test",
        schema: {
            "urn": "surf:harrytest",
            "description": "S3 Project harry-test",
        },
    }
    entry = mapping.scim_group_to_group_ldap(
        resource, "@all", co_display_name="harry-test"
    )
    assert entry["cn"] == ["@all"]
    assert entry["displayName"] == ["All Members of harry-test"]
    assert entry["description"] == ["All CO members"]


def test_flat_group_entry_copies_co_attrs():
    ordered = {
        "objectClass": ["groupOfMembers", "extensibleObject"],
        "cn": ["@all"],
        "displayName": ["All Members of harry-test"],
        "description": ["All CO members"],
    }
    entry = flat.flat_group_entry(
        ordered,
        "surf.harrytest",
        "@all",
        ["uid=alice,ou=People,dc=flat,dc=x"],
        co_attrs={
            "mail": ["a@example.org"],
            "organizationalStatus": ["active"],
        },
    )
    assert entry["cn"] == ["surf.harrytest.@all"]
    assert entry["mail"] == ["a@example.org"]
    assert entry["organizationalStatus"] == ["active"]


def test_scim_group_to_group_ldap_labeled_uri():
    schema = mapping.sram_group_schema()
    resource = {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee@sram.surf.nl",
        "externalId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee@sram.surf.nl",
        "displayName": "admin",
        schema: {
            "urn": "surf:demo1:admin",
            "description": "Project administrator",
            "links": [{"name": "sbs_url", "value": "https://example/g"}],
        },
    }
    entry = mapping.scim_group_to_group_ldap(resource, "admin")
    assert entry["cn"] == ["admin"]
    assert entry["uniqueIdentifier"] == [
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    ]
    assert entry["labeledURI"] == ["https://example/g sbs_url"]
    assert entry["description"] == ["Project administrator"]


def test_bare_unique_identifier():
    assert mapping.bare_unique_identifier(
        "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58@sram.surf.nl"
    ) == "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58"
    assert mapping.bare_unique_identifier("plain-uuid") == "plain-uuid"
    assert mapping.bare_unique_identifier(None) is None


def test_is_collaboration_group():
    schema = mapping.sram_group_schema()
    co = {
        "displayName": "My CO",
        schema: {
            "urn": "org1.co1",
            "links": [{"name": "sbs_url", "value": "https://sbs/collaborations/1"}],
        },
    }
    assert mapping.is_collaboration_group(co) is True

    sbs_co = {
        "displayName": "demo1",
        schema: {"urn": "surf:demo1"},
    }
    assert mapping.is_collaboration_group(sbs_co) is True

    subgroup = {
        "displayName": "Admins",
        schema: {"urn": "org1.co1:admins"},
    }
    assert mapping.is_collaboration_group(subgroup) is False

    sbs_subgroup = {
        "displayName": "admin",
        schema: {"urn": "surf:demo1:admin"},
    }
    assert mapping.is_collaboration_group(sbs_subgroup) is False


def test_merge_vo_person_status():
    assert flat.merge_vo_person_status(["expired", "active"]) == "active"
    assert flat.merge_vo_person_status(["expired", "expired"]) == "expired"


def test_scim_store_identifiers_keeps_server_and_external_id():
    values = mapping.scim_store_identifiers(
        "server-uuid-1",
        "client-uuid-1@sram.surf.nl",
    )
    assert values == ["server-uuid-1", "client-uuid-1@sram.surf.nl"]
    scim_id, external_id = mapping.split_scim_store_identifiers(values)
    assert scim_id == "server-uuid-1"
    assert external_id == "client-uuid-1@sram.surf.nl"


def test_group_unique_identifier_is_bare_only():
    assert mapping.group_unique_identifier(
        "server-generated-uuid",
        "fb9ce3da-0242-4fe4-9ea5-462d0cdfec58@sram.surf.nl",
    ) == ["fb9ce3da-0242-4fe4-9ea5-462d0cdfec58"]
    assert mapping.group_unique_identifier(
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee@sram.surf.nl"
    ) == ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"]


def test_plugin_id_is_server_generated_not_external_id():
    from data.plugins.sram_ldap.plugin import SRAM_LDAP_Plugin

    plugin = object.__new__(SRAM_LDAP_Plugin)
    first = plugin.id({"externalId": "always-the-same@sram.surf.nl"})
    second = plugin.id({"externalId": "always-the-same@sram.surf.nl"})
    assert first != "always-the-same@sram.surf.nl"
    assert first != second


def test_rewrite_members_to_flat():
    base = "dc=svc,dc=example,dc=org"
    ordered = [
        f"uid=alice,ou=People,o=org1.co1,dc=ordered,{base}",
        f"uid=bob,ou=People,o=org1.co1,dc=ordered,{base}",
    ]
    assert flat.rewrite_members_to_flat(ordered, base) == [
        f"uid=alice,ou=People,dc=flat,{base}",
        f"uid=bob,ou=People,dc=flat,{base}",
    ]
