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

## PR workflow

```bash
git push -u origin feature/sram-ldap-ordered-flat
gh pr create --title "Add SRAM ordered LDAP plugin with flat derive" ...
```

SDP deploy track: [`../SDP/scim-server/docs/PLSC-MIGRATION.md`](../../SDP/scim-server/docs/PLSC-MIGRATION.md)
(or the copy under your SDP checkout).

## Status

Scaffold + mapping/DIT/flat unit tests green. End-to-end LDAP integration
tests (against OpenLDAP with SRAM schemas) are the next increment before PR.
