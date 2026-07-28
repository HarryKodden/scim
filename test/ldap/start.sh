#!/usr/bin/env bash
# Start a local OpenLDAP with SRAM schemas for SCIM LDAP_LAYOUT=sram-ordered tests.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

CONTAINER_TOOL="${CONTAINER_TOOL:-docker}"
COMPOSE="${CONTAINER_TOOL} compose"

echo "Starting OpenLDAP..."
$COMPOSE up -d

echo "Waiting for slapd..."
for i in $(seq 1 30); do
  if $CONTAINER_TOOL exec scim-sram-ldap \
      ldapsearch -x -H ldap://localhost \
      -b "dc=sram,dc=tld" \
      -D "cn=admin,dc=sram,dc=tld" -w secret \
      "(objectClass=*)" dn >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Loading SRAM schemas (idempotent-ish)..."
$CONTAINER_TOOL cp "$ROOT/ldif" scim-sram-ldap:/tmp/ldif

load_config() {
  local file="$1"
  $CONTAINER_TOOL exec scim-sram-ldap \
    ldapadd -c -H ldap://localhost \
    -D "cn=admin,cn=config" -w config \
    -f "/tmp/ldif/$file" 2>/dev/null || true
}

load_config access.ldif
load_config config.ldif
load_config eduPerson.ldif
load_config voPerson.ldif
load_config groupOfMembers.ldif
load_config sramPerson.ldif

echo "Bootstrapping pilot service base DN..."
$CONTAINER_TOOL cp "$ROOT/bootstrap/01-base.ldif" scim-sram-ldap:/tmp/01-base.ldif
$CONTAINER_TOOL exec scim-sram-ldap \
  ldapadd -c -H ldap://localhost \
  -D "cn=admin,dc=sram,dc=tld" -w secret \
  -f /tmp/01-base.ldif 2>/dev/null || true

echo
echo "LDAP ready."
echo "  Host:     localhost:1389"
echo "  Base DN:  dc=pilot,dc=services,dc=sram,dc=tld"
echo "  Bind DN:  cn=admin,dc=sram,dc=tld"
echo "  Password: secret"
echo
echo "SCIM env:"
echo "  LDAP_HOSTNAME=localhost"
echo "  LDAP_PORT=1389"
echo "  LDAP_BASENAME=dc=pilot,dc=services,dc=sram,dc=tld"
echo "  LDAP_USERNAME=cn=admin,dc=sram,dc=tld"
echo "  LDAP_PASSWORD=secret"
echo "  LDAP_LAYOUT=sram-ordered"
echo "  LDAP_FLAT_DERIVE=true"
echo
echo "Or URI form: LDAP_HOSTNAME=ldap://localhost:1389"
echo
echo "Inspect:  ldapsearch -x -H ldap://localhost:1389 -D cn=admin,dc=sram,dc=tld -w secret -b dc=pilot,dc=services,dc=sram,dc=tld"
