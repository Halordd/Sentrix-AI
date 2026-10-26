#!/usr/bin/env bash
set -euo pipefail

DB_HOST="${SENTRIX_DB_HOST:-10.20.10.20}"
DB_USER="${SENTRIX_DB_USER:-sentrix_migrator}"
TARGET_DB="${1:-}"
DUMP="${2:-}"

if [[ -z "$TARGET_DB" || -z "$DUMP" ]]; then
  echo "usage: $0 <target_database> <dump_file>" >&2
  exit 2
fi
if [[ ! -f "$DUMP" ]]; then
  echo "dump not found: $DUMP" >&2
  exit 2
fi
if [[ "$TARGET_DB" == "sentrix" ]]; then
  echo "refusing to restore over the live sentrix database" >&2
  exit 3
fi

pg_restore -h "$DB_HOST" -U "$DB_USER" -d "$TARGET_DB" \
  --clean --if-exists --no-owner "$DUMP"
echo "restored $DUMP into $TARGET_DB"
