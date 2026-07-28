# Local test LDAP + SCIM→LDAP fixtures (PLSC-style)

OpenLDAP with SRAM schemas, plus **repeatable SCIM operation sequences** that
are applied and then verified by reading LDAP back (same idea as PLSC’s
`api/plsc/sync` replay + `SLdap.find` asserts).

## Start / stop LDAP

```bash
./test/ldap/start.sh
./test/ldap/stop.sh
```

| Setting | Value |
| --- | --- |
| URL | `ldap://localhost:1389` |
| Bind DN | `cn=admin,dc=sram,dc=tld` |
| Password | `secret` |
| `LDAP_BASENAME` | `dc=pilot,dc=services,dc=sram,dc=tld` |

## Integration fixtures

| Path | Role |
| --- | --- |
| `test/ldap/fixtures/<name>/sequence.json` | Ordered SCIM ops + LDAP assertions |
| `test/ldap/lib/scim_apply.py` | Apply ops (plugin or HTTP) + assert LDAP |
| `test/ldap/lib/ldap_assert.py` | LDAP find / wipe helpers |
| `test/ldap/test_integration.py` | Pytest runner |
| `test/ldap/run_integration.sh` | One-shot: ensure LDAP + run pytest |

### Coverage matrix

| SCIM variation | Fixture | Notes |
| --- | --- | --- |
| Create User | `minimal`, `lifecycle` | Holding OU until CO membership |
| Create Group (CO / `@all`) | `minimal`, `lifecycle` | SRAM `urn` + `links` |
| Create Group (subgroup) | `minimal`, `lifecycle` | `urn` = `org.co:group` |
| Add User to Group | `lifecycle` `05_add_bob_to_group` | PUT Group with expanded `members` |
| Remove User from Group | `lifecycle` `06_remove_alice_from_group` | PUT Group; person DN kept under CO |
| Update User | `lifecycle` `07_update_user_alice` | displayName / mail / sn |
| Update Group | `lifecycle` `08_update_group_co` | CO + `@all` displayName/description |
| Deactivate User | `lifecycle` `09_deactivate_user_alice` | ordered + flat `voPersonStatus=expired` |
| Delete Group | `lifecycle` `10`/`11` | subgroup then CO `@all` |
| Delete User | `lifecycle` `12`/`13` | ordered + flat People |
| Flat after remove-from-group | `lifecycle` `06` | flat `@all` members = bob only |
| Flat after update user | `lifecycle` `07` | flat People mail/displayName/sn |
| Flat after update group | `lifecycle` `08` | flat `@all` displayName |
| User in multiple COs | `multi_co` | one flat Person, two flat `@all` groups |

**Also worth adding later (not in fixtures yet):**

| Variation | Why |
| --- | --- |
| SSH keys | `ldapPublicKey` / `sshPublicKey` |
| Empty members after remove-all | `@all` with no `member` attr |
| PATCH vs PUT | HTTP PATCH path (plugin treats as full replace) |
| Re-activate user | `active=true` after expired |
| Delete CO while members remain | Orphan People under `o=` |
| Per-CO status diverge → flat active-wins | Needs membership-level status (SCIM User.active is global today); unit-tested in `test_sram_ldap.py` |

## Fixture format

```json
{
  "name": "minimal",
  "operations": [
    {"name": "01_create_user", "op": "POST", "resourceType": "User", "body": { "...SCIM User..." }},
    {"name": "02_create_co", "op": "POST", "resourceType": "Group", "body": { "...SCIM Group with urn..." }}
  ],
  "assertions": [
    {
      "dn": "uid=alice,ou=People,o=orgdemo.c1,dc=ordered,${LDAP_BASENAME}",
      "attrs": { "uid": ["alice"], "mail": ["alice@example.org"] }
    }
  ]
}
```

`${LDAP_BASENAME}` is substituted at assert time.

### Replay (default — like PLSC without `SBS_URL`)

In-process plugin writes to local LDAP:

```bash
./test/ldap/run_integration.sh
# or:
SCIM_MODE=plugin pytest -q --confcutdir=test/ldap test/ldap/test_integration.py
```

### Live SCIM HTTP (like PLSC with `SBS_URL`)

Point at playground (or local uvicorn). LDAP asserts still need a reachable
directory (local OpenLDAP, or cluster LDAP if you can port-forward):

```bash
export SCIM_MODE=http
export SCIM_URL=https://scim-server.playground.sdp.surf.nl/api/v2
export SCIM_API_KEY=chooseyourownsecret
# LDAP_* must reach the same directory the server writes to
./test/ldap/run_integration.sh
```

### Record HTTP step results

```bash
SCIM_MODE=http SCIM_URL=… SCIM_API_KEY=… SCIM_API_RECORDING=YES \
  pytest -q --confcutdir=test/ldap test/ldap/test_integration.py
# writes test/ldap/fixtures/_recorded/*.json
```

## Adding a fixture

1. Copy `fixtures/minimal/` to `fixtures/<newname>/`
2. Edit `sequence.json` operations (SCIM User/Group bodies with SRAM extensions)
3. Fill `assertions` with expected ordered/flat DNs and attrs
4. Re-run `./test/ldap/run_integration.sh`

Tip: after a successful plugin run, inspect with:

```bash
ldapsearch -x -H ldap://localhost:1389 \
  -D cn=admin,dc=sram,dc=tld -w secret \
  -b dc=pilot,dc=services,dc=sram,dc=tld '(objectClass=*)' dn
```
