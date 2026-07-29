# SCIM ↔ LDAP attribute mapping (SRAM plugin)

Source of truth: `code/data/plugins/sram_ldap/mapping.py` (SCIM→LDAP) and
`plugin.py` `_get_user` / `_get_group` (LDAP→SCIM).

Extension schema URIs (configurable via `SRAM_SCIM_SCHEMA`, default
`urn:mace:surf.nl:sram:scim:extension`):

| Resource | Extension URI |
| --- | --- |
| User | `{SRAM_SCIM_SCHEMA}:User` |
| Group | `{SRAM_SCIM_SCHEMA}:Group` |

Below, `ext.*` means a field under the SRAM extension object.

---

## Identifiers (`id` vs `externalId`)

| Concept | SCIM | LDAP |
| --- | --- | --- |
| Server primary key | `id` (always UUID from `Plugin.id()`) | Persons (ordered only): **first** `uniqueIdentifier` |
| Client correlation | `externalId` (SBS, often `uuid@sram.surf.nl`) | Persons (ordered only): **second** `uniqueIdentifier` (prefer value with `@`) |
| Group / CO SBS id | `externalId` (or bare form of `id`) | Single `uniqueIdentifier` = **bare UUID** (no `@realm`) |

Person overlay helpers:

- Write: `scim_store_identifiers(scim_id, external_id)` → `[id, externalId…]`
- Read: `split_scim_store_identifiers(values)` → `(id, externalId)`  
  - `id` = first value  
  - `externalId` = first value containing `@`, else second value, else first

Flat persons **drop** `uniqueIdentifier` and `extensibleObject` (SRAM service shape).
Ordered persons keep them so `GET /Users/{id}` and Group `members.value` resolve.

---

## User / person

### SCIM → LDAP (`scim_user_to_ldap` + person overlay)

| SCIM | LDAP | Notes |
| --- | --- | --- |
| `userName` | `uid` (RDN) | Required |
| `displayName` | `displayName` | Default `n/a` |
| `name.givenName` | `givenName` | Default `n/a` |
| `name.familyName` | `sn` | Default `n/a` |
| `emails[]` (primary, else first) | `mail` | Omitted if empty |
| `active` | `voPersonStatus` | `true`→`active`, `false`→`expired` |
| `ext.eduPersonUniqueId` \|\| `externalId` \|\| `userName` | `cn`, `eduPersonUniqueId` | Same value for both |
| `ext.voPersonExternalAffiliation` | `voPersonExternalAffiliation` | String split on `,` or list |
| `ext.voPersonExternalId` | `voPersonExternalID` | |
| `ext.eduPersonScopedAffiliation` | `eduPersonScopedAffiliation` | Else hardcoded `member@sram.surf.nl` |
| `ext.sramInactiveDays` | `sramInactiveDays` | Stringified |
| `ext.voPersonPolicyAgreement[]` | `voPersonPolicyAgreement` or `voPersonPolicyAgreement;time-<epoch>` | SBS `{url,agreed_at}` (`value`/`time` accepted as fallback) |
| `x509Certificates[].value` | `sshPublicKey` + OC `ldapPublicKey` | Base64-decoded if needed |
| `id` + `externalId` (overlay) | `uniqueIdentifier` (multi) + OC `extensibleObject` | Ordered only; stripped on flat |
| — | `objectClass` | `inetOrgPerson`, `person`, `eduPerson`, `voPerson`, `sramPerson` [+`ldapPublicKey`] |

DN (ordered): `uid=<userName>,ou=People,o=<org.co>,dc=ordered,<LDAP_BASENAME>`  
DN (flat): `uid=<userName>,ou=People,dc=flat,<LDAP_BASENAME>`

### LDAP → SCIM (`_get_user`)

| LDAP | SCIM | Notes |
| --- | --- | --- |
| `uniqueIdentifier` (split) | `id`, `externalId` | See identifier rules above |
| `uid` | `userName` | |
| `displayName` | `displayName` | |
| `givenName` | `name.givenName` | |
| `sn` | `name.familyName` | |
| `mail` | `emails[0].value` + `primary: true` | Single primary only on read |
| `voPersonStatus` | `active` | `active` iff value == `active` |
| `eduPersonUniqueId` | `ext.eduPersonUniqueId` | Also fallback for `externalId` |
| `voPersonExternalID` | `ext.voPersonExternalId` | |
| `voPersonExternalAffiliation` | `ext.voPersonExternalAffiliation` | First value only |
| `sramInactiveDays` | `ext.sramInactiveDays` | First value only |
| `sshPublicKey` | *(not currently reconstructed)* | Written but not returned on GET |
| `voPersonPolicyAgreement;time-*` | `ext.voPersonPolicyAgreement[]` | `{url, agreed_at}` only |

Lookup keys for GET: `uniqueIdentifier`, `eduPersonUniqueId`, or `cn` matching the path id.

---

## Group / collaboration

Collaboration vs subgroup is detected by `ext.links` containing `sbs_url`, or by
`ext.urn` having no group segment (`org.co` vs `org.co:admins`).

### Collaboration (CO) — SCIM → LDAP org entry

DN: `o=<org.co>,dc=ordered,<LDAP_BASENAME>`  
Also creates `@all` under `ou=Groups`.

| SCIM | LDAP (organization) | Notes |
| --- | --- | --- |
| `ext.urn` → parsed | `o` | e.g. `surf:harrytest` → `surf.harrytest` |
| `externalId` \|\| `id` | `uniqueIdentifier` | Bare UUID |
| `displayName` | `displayName` | Else last segment of `o` |
| `ext.description` | `description` | |
| `ext.labels` | `businessCategory` | |
| `ext.links[]` `{name,value}` | `labeledURI` | `"<url> <name>"` (spaces in URL → `%20`) |
| `emails[]` and/or `ext.mail` / `ext.emails` | `mail` | Else filled from member mails |
| `ext.organizationalStatus` \|\| `active` | `organizationalStatus` | Default `active` |
| — | `objectClass` | `top`, `organization`, `extensibleObject` |

### `@all` / subgroup — SCIM → LDAP group entry

DN ordered: `cn=<cn>,ou=Groups,o=<org.co>,dc=ordered,<LDAP_BASENAME>`  
DN flat: `cn=<org.co>.<cn>,ou=Groups,dc=flat,<LDAP_BASENAME>`

| SCIM | LDAP (`groupOfMembers`) | Notes |
| --- | --- | --- |
| `ext.urn` group part | `cn` | `@all` for collaboration; else subgroup cn |
| `externalId` \|\| `id` | `uniqueIdentifier` | Bare UUID (`group_unique_identifier`) |
| Collaboration | `displayName` | `All Members of <CO displayName>` |
| Collaboration | `description` | Fixed `All CO members` |
| Subgroup `displayName` | `displayName` | |
| Subgroup `ext.description` | `description` | |
| `ext.links[]` | `labeledURI` | Subgroups inherit CO `labeledURI` if omitted |
| `members[].value` | `member` (person DNs) | Resolved via User `id` or `externalId` → `uid` |
| — | `objectClass` | `extensibleObject`, `groupOfMembers` |

Flat groups also get CO `mail` + `organizationalStatus` projected onto the entry.

### LDAP → SCIM (`_get_group`)

| LDAP | SCIM | Notes |
| --- | --- | --- |
| `uniqueIdentifier` (split / bare) | `id`, `externalId` | Same split helpers; bare UUID may be both |
| `displayName` | `displayName` | |
| `description` | `ext.description` | |
| DN `o=` + `cn` | `ext.urn` | `org.co` or `org.co:group` (`@all` → CO urn only) |
| `labeledURI` | `ext.links[]` | `"<url> <name>"` → `{name, value}` |
| `member` person DNs | `members[]` | `value` = user SCIM `id`; `display` = person `displayName`; `$ref` = `/Users/{id}` |
| CO `mail` / `organizationalStatus` | *(not on Group GET)* | Live on CO org + flat groups only |

---

## Round-trip gaps (known)

These are written SCIM→LDAP but **not** (fully) restored LDAP→SCIM today:

| Direction | Attribute |
| --- | --- |
| User GET | `sshPublicKey` / `x509Certificates` |
| User GET | multi-value affiliations (first only) |
| Group GET | CO `mail`, `organizationalStatus`, `labels`/`businessCategory` |

Membership write accepts `members.value` as server `id` **or** `externalId`;
read returns server `id` with human `display` (user name), matching SBS style.

---

## Code map

| Direction | Entry point |
| --- | --- |
| User SCIM → LDAP | `mapping.scim_user_to_ldap` + `plugin._apply_person_scim_overlay` |
| User LDAP → SCIM | `plugin._get_user` |
| CO SCIM → LDAP | `mapping.scim_group_to_co_ldap` |
| Group SCIM → LDAP | `mapping.scim_group_to_group_ldap` (+ inherit CO `labeledURI`) |
| Group LDAP → SCIM | `plugin._get_group` |
| Flat derive | `flat.flat_person_entry` / `flat.flat_group_entry` |
