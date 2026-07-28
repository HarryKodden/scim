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


def test_scim_group_to_group_ldap_labeled_uri():
    schema = mapping.sram_group_schema()
    resource = {
        "displayName": "admin",
        schema: {
            "urn": "surf:demo1:admin",
            "description": "Project administrator",
            "links": [{"name": "sbs_url", "value": "https://example/g"}],
        },
    }
    entry = mapping.scim_group_to_group_ldap(resource, "admin")
    assert entry["cn"] == ["admin"]
    assert entry["labeledURI"] == ["https://example/g sbs_url"]


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
