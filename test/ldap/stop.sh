#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
CONTAINER_TOOL="${CONTAINER_TOOL:-docker}"
$CONTAINER_TOOL compose down -v
echo "LDAP stopped (volumes removed)."
