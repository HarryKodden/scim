# SRAM LDAP compatibility findings (playground vs service LDAP)

Date: 2026-07-28  
Compared:

| Source | Base |
| --- | --- |
| **SRAM service LDAP** | `ldaps://ldap.sram.surf.nl` · `dc=<service-uuid>,dc=services,dc=sram,dc=surf,dc=nl` |
| **SCIM → OpenLDAP (SDP playground)** | in-cluster · `dc=pilot,dc=services,dc=sram,dc=tld` · `LDAP_LAYOUT=sram-ordered` |

Goal: SCIM-written LDAP must be **layout- and attribute-compatible** with SRAM’s own service LDAP so consumers can switch without remapping.

> **Root cause of playground layout mismatch:** `parse_group_urn` treated SBS
> `surf:demo1:admin` as CO=`surf` + group=`demo1.admin`. Fixed to CO=`surf.demo1`
> + `cn=admin` (see `dit.parse_group_urn`). Rebuild the SDP image from this
> branch tip and re-provision to verify.

## 1. Ordered DIT layout (critical)

### SRAM (reference)

```
dc=<service>,…
├── cn=admin
└── dc=ordered
    └── o=surf.harrytest          ← one organization entry per CO
        ├── ou=People
        │   └── uid=dsalek2
        └── ou=Groups
            ├── cn=@all
            ├── cn=admin
            └── cn=members
```

No `dc=flat` under this service base (ordered only in the dump).

### SCIM playground (observed)

```
dc=pilot,…
├── dc=flat
│   ├── ou=People / ou=Groups
│   └── cn=surf.demo1.admin, cn=surf.@all, …
└── dc=ordered
    ├── o=surf                    ← org, not CO
    │   ├── ou=People
    │   └── ou=Groups
    │       ├── cn=demo1.admin    ← CO.group in cn
    │       └── cn=harrytest.members
    ├── ou=People                 ← also people at ordered root
    └── o=orgldap.c1
```

### Expected on this branch (`dit.py`)

| Helper | DN |
| --- | --- |
| `co_dn(co)` | `o={co},dc=ordered,{base}` |
| `person_dn(uid, co)` | `uid={uid},ou=People,o={co},dc=ordered,{base}` |
| `ordered_group_dn(cn, co)` | `cn={cn},ou=Groups,o={co},dc=ordered,{base}` |
| flat (optional) | `cn={co}.{group},ou=Groups,dc=flat,{base}` |

**Action:** Ensure runtime writes match `dit.py` (CO identifier = full `org.co`, e.g. `surf.harrytest`). Fix whatever still emits `o=surf` + dotted group CNs in ordered. Re-verify after SDP image rebuild from this branch tip.

## 2. Entry-level attribute gaps

### Person (side-by-side: `uid=dsalek2`, `uid=hkodden14`)

**Compatible (same values):** `cn`, `displayName`, `givenName`, `sn`, `mail`, `uid`, `eduPersonUniqueId`, `eduPersonScopedAffiliation`, `voPersonExternalID`, `voPersonExternalAffiliation`, `voPersonStatus`, core objectClasses (`person`, `inetOrgPerson`, `eduPerson`, `voPerson`, `sramPerson`).

| Issue | SRAM | SCIM (playground) | Action |
| --- | --- | --- | --- |
| Policy agreement | `voPersonPolicyAgreement;time-<epoch>` | missing | Map / write from SCIM if present in payload |
| SSH keys | `sshPublicKey` + `ldapPublicKey` OC (some users) | missing | Map when provided |
| `uniqueIdentifier` | absent on these persons | present (UUID) | Confirm whether SRAM omits on purpose; drop or align |
| `extensibleObject` | not on person | present | Prefer match SRAM (omit unless required) |
| `sramInactiveDays` | CO-scoped (e.g. 14) | may differ (e.g. 21) | Use CO membership context, not a global/default |

### Group (`cn=admin` / `cn=members` vs `cn=demo1.admin` / `cn=harrytest.members`)

| Issue | SRAM | SCIM | Action |
| --- | --- | --- | --- |
| `cn` | short name under CO (`admin`, `members`) | dotted under org | Fixed by correct ordered DIT |
| `objectClass` | `groupOfMembers` + `extensibleObject` | same | OK |
| `labeledURI` | sometimes present | often missing | Map when in SCIM |
| `uniqueIdentifier` | bare UUID | bare UUID (no `@realm`) | Aligned |
| Holding OU people | none | transient until membership | Place under CO People and delete holding on group write |
| `cn=@all` stub | always present | created with CO containers | Aligned |


### CO / organization entry

SRAM CO entry `o=surf.harrytest` includes: `mail` (multi), `organizationalStatus`, `labeledURI` (sbs_url + logo), `description`, `displayName`, `uniqueIdentifier` (CO uuid without `@realm`).

SCIM org entry observed as `o=surf` (wrong level) with similar URI/description pattern but:

| Issue | Action |
| --- | --- |
## Remaining gaps (post 2026-07-29)

| Issue | Notes |
| --- | --- |
| Ordered person `uniqueIdentifier` + `extensibleObject` | SCIM-store overlay (OpenLDAP requires extensibleObject for uniqueIdentifier); both stripped on flat |
| `voPersonPolicyAgreement;time-*` | **SBS → SCIM payload** must include it; mapping already writes when present |
| CO `mail` | Only from Group.emails in SCIM (not synthesized from members) |
| Group `uniqueIdentifier` | Bare UUID only (SRAM) |

Local verification: `pytest test/test_sram_format.py test/test_sram_ldap.py`




### Service base

SRAM base has `labeledURI` / `labeledURIObject`. SCIM pilot base lacked `labeledURIObject`. Optional for consumers; add if mirroring service root.

## 3. Suggested verification loop

1. Fix mapping / DIT so ordered matches SRAM (CO-as-`o=`).
2. Rebuild SDP image from this branch tip (`SCIM_REV` bump).
3. Re-dump playground LDAP and SRAM service LDAP.
4. Diff one CO (`surf.harrytest`) person + group + org entry.

## 4. Non-goals / expected differences

- Different service base DN (`dc=pilot,…` vs `dc=<uuid>,dc=services,dc=sram,dc=surf,dc=nl`) — fine.
- Independent `uniqueIdentifier` values if SCIM and SRAM LDAP are not the same writer — fine once *format* aligns.
- Flat tree only when `LDAP_FLAT_DERIVE=true`; SRAM service dump may be ordered-only.
