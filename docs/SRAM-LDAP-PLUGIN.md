# SRAM LDAP plugin (feature branch)

Branch: **`feature/sram-ldap-ordered-flat`**

Clone of [HarryKodden/scim](https://github.com/HarryKodden/scim) with a new
plugin that replaces PLSC’s ordered + flat LDAP writers.

## Layout

| Path | Role |
| --- | --- |
| `code/data/plugins/sram_ldap/` | New plugin package |
| `code/data/plugins/ldap.py` | Unchanged generic LDAP backend |
| `code/data/__init__.py` | Selects SRAM plugin when `LDAP_LAYOUT=sram-ordered` |
| `test/test_sram_ldap.py` | Unit tests for mapping / DIT / flat helpers |

## Activate

```bash
LDAP_HOSTNAME=...
LDAP_BASENAME=dc=<service>,...
LDAP_LAYOUT=sram-ordered
LDAP_FLAT_DERIVE=true
```

## Local test LDAP

```bash
./test/ldap/start.sh
./test/ldap/run_integration.sh   # SCIM op sequence → assert LDAP
```

See [`test/ldap/README.md`](../test/ldap/README.md) for fixture format, plugin
vs HTTP modes, and recording (PLSC-style replay/verify).

Uses PLSC SRAM schemas and base DN `dc=pilot,dc=services,dc=sram,dc=tld` on
`localhost:1389`.

## SDP playground pilot (SRAM → SCIM → LDAP)

See [`../SDP/scim-server/docs/SRAM-PILOT.md`](../../SDP/scim-server/docs/SRAM-PILOT.md)
for enabling SBS SCIM against playground and dumping in-cluster LDAP.

**Before deploy:** push this branch (plugin write fixes + fixtures) so SDP’s
`SCIM_REF=feature/sram-ldap-ordered-flat` image rebuild includes them.

## PR workflow

```bash
git push -u origin feature/sram-ldap-ordered-flat
gh pr create --title "Add SRAM ordered LDAP plugin with flat derive" ...
```

SDP deploy track: [`../SDP/scim-server/docs/PLSC-MIGRATION.md`](../../SDP/scim-server/docs/PLSC-MIGRATION.md)
(or the copy under your SDP checkout).

## Compatibility vs SRAM service LDAP

Playground SCIM LDAP was compared to a real SRAM service LDAP
(`ldaps://ldap.sram.surf.nl`). Findings and follow-ups:

→ [`SRAM-LDAP-COMPATIBILITY.md`](SRAM-LDAP-COMPATIBILITY.md)

## Status

Unit tests + local OpenLDAP integration fixtures (`minimal`, `lifecycle`,
`multi_co`) green. Push this branch before SDP rebuild so playground picks up
plugin write fixes.
