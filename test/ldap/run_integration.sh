#!/usr/bin/env bash
# Run SCIM→LDAP integration fixtures (plugin mode against local OpenLDAP).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if ! ldapsearch -x -H "ldap://${LDAP_HOSTNAME:-localhost}:${LDAP_PORT:-1389}" \
    -D "${LDAP_USERNAME:-cn=admin,dc=sram,dc=tld}" \
    -w "${LDAP_PASSWORD:-secret}" \
    -b "${LDAP_BASENAME:-dc=pilot,dc=services,dc=sram,dc=tld}" \
    -s base dn >/dev/null 2>&1; then
  echo "LDAP not up — starting test/ldap ..."
  ./test/ldap/start.sh
fi

export LDAP_HOSTNAME="${LDAP_HOSTNAME:-localhost}"
export LDAP_PORT="${LDAP_PORT:-1389}"
export LDAP_BASENAME="${LDAP_BASENAME:-dc=pilot,dc=services,dc=sram,dc=tld}"
export LDAP_USERNAME="${LDAP_USERNAME:-cn=admin,dc=sram,dc=tld}"
export LDAP_PASSWORD="${LDAP_PASSWORD:-secret}"
export LDAP_LAYOUT=sram-ordered
export LDAP_FLAT_DERIVE=true
export SCIM_MODE="${SCIM_MODE:-plugin}"
export PYTHONPATH="${ROOT}/code${PYTHONPATH:+:$PYTHONPATH}"

if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec pytest -q --confcutdir=test/ldap test/ldap/test_integration.py "$@"
