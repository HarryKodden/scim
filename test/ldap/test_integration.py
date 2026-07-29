"""
SCIM → LDAP integration tests (PLSC-style).

Requires local OpenLDAP from ``./test/ldap/start.sh``.

Modes (env):
  SCIM_MODE=plugin   (default) — apply fixture ops to SRAM_LDAP_Plugin in-process
  SCIM_MODE=http + SCIM_URL=… — POST sequence to a live SCIM server, then assert LDAP

  SCIM_API_RECORDING=YES — when http mode, write step/result JSON under
    test/ldap/fixtures/_recorded/
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIB = Path(__file__).resolve().parent / "lib"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(LIB))

from ldap_assert import ldap_connect, wipe_provisioned  # noqa: E402
from scim_apply import apply_sequence, assert_ldap, load_sequence  # noqa: E402

BASENAME = os.environ.get(
    "LDAP_BASENAME", "dc=pilot,dc=services,dc=sram,dc=tld"
)


def _ldap_reachable() -> bool:
    try:
        conn = ldap_connect()
        conn.unbind()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _ldap_reachable(),
    reason="LDAP not reachable; run ./test/ldap/start.sh first",
)


@pytest.fixture
def ldap_env(monkeypatch):
    monkeypatch.setenv("LDAP_HOSTNAME", os.environ.get("LDAP_HOSTNAME", "localhost"))
    monkeypatch.setenv("LDAP_PORT", os.environ.get("LDAP_PORT", "1389"))
    monkeypatch.setenv("LDAP_BASENAME", BASENAME)
    monkeypatch.setenv(
        "LDAP_USERNAME",
        os.environ.get("LDAP_USERNAME", "cn=admin,dc=sram,dc=tld"),
    )
    monkeypatch.setenv(
        "LDAP_PASSWORD", os.environ.get("LDAP_PASSWORD", "secret")
    )
    monkeypatch.setenv("LDAP_LAYOUT", "sram-ordered")
    monkeypatch.setenv("LDAP_FLAT_DERIVE", "true")
    monkeypatch.setenv(
        "SRAM_SCIM_SCHEMA", "urn:mace:surf.nl:sram:scim:extension"
    )
    # Avoid data/__init__ picking generic LDAP when importing plugin package
    monkeypatch.setenv("LDAP_LAYOUT", "sram-ordered")


@pytest.fixture
def clean_ldap(ldap_env):
    conn = ldap_connect()
    wipe_provisioned(conn, BASENAME)
    yield conn
    wipe_provisioned(conn, BASENAME)
    conn.unbind()


@pytest.mark.parametrize(
    "fixture_name",
    sorted(
        p.name
        for p in FIXTURES.iterdir()
        if p.is_dir() and (p / "sequence.json").exists() and not p.name.startswith("_")
    ),
)
def test_scim_sequence_ldap_state(fixture_name, clean_ldap, ldap_env):
    sequence = load_sequence(FIXTURES / fixture_name / "sequence.json")
    apply_sequence(sequence, conn=clean_ldap)
    assert_ldap(sequence, clean_ldap)


def test_group_extension_links_from_ldap(clean_ldap, ldap_env):
    sequence = load_sequence(FIXTURES / "minimal" / "sequence.json")
    apply_sequence(sequence, conn=clean_ldap)

    from data.plugins.sram_ldap.plugin import SRAM_LDAP_Plugin
    from data.plugins.sram_ldap import mapping

    host = os.environ.get("LDAP_HOSTNAME", "localhost")
    basename = os.environ.get(
        "LDAP_BASENAME", "dc=pilot,dc=services,dc=sram,dc=tld"
    )
    user = os.environ.get(
        "LDAP_USERNAME", "cn=admin,dc=sram,dc=tld"
    )
    password = os.environ.get("LDAP_PASSWORD", "secret")
    flat = os.environ.get("LDAP_FLAT_DERIVE", "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    Groups = SRAM_LDAP_Plugin("Groups", host, basename, user, password, flat)
    group_id = "22222222-2222-2222-2222-222222222222"
    group = Groups[group_id]

    ext = group.get(mapping.sram_group_schema()) or {}
    links = ext.get("links") or []
    assert sorted(
        [(l["name"], l["value"]) for l in links]
    ) == sorted(
        [
            (
                "sbs_url",
                "https://sbs.example/collaborations/22222222-2222-2222-2222-222222222222",
            ),
            ("logo", "https://example.org/logo.png"),
        ]
    )

    # Subgroups should inherit CO sbs_url/logo labels (SRAM behavior).
    subgroup_id = "33333333-3333-3333-3333-333333333333"
    subgroup = Groups[subgroup_id]
    subext = subgroup.get(mapping.sram_group_schema()) or {}
    sublinks = subext.get("links") or []
    assert sorted(
        [(l["name"], l["value"]) for l in sublinks]
    ) == sorted(
        [
            (
                "sbs_url",
                "https://sbs.example/collaborations/22222222-2222-2222-2222-222222222222",
            ),
            ("logo", "https://example.org/logo.png"),
        ]
    )
