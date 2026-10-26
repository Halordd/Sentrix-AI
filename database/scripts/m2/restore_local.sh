#!/usr/bin/env bash
# Run this on VM02 as the postgres OS user:
#   sudo -u postgres bash restore_local.sh <target_db> <dump_file>
set -euo pipefail

TARGET_DB="${1:-}"
DUMP="${2:-}"

if [[ -z "$TARGET_DB" || -z "$DUMP" ]]; then
  echo "usage: sudo -u postgres bash $0 <target_db> <dump_file>" >&2
  exit 2
fi
if [[ "$TARGET_DB" == "sentrix" ]]; then
  echo "refusing to restore over the live sentrix database" >&2
  exit 3
fi
if [[ ! -f "$DUMP" ]]; then
  echo "dump not found: $DUMP" >&2
  exit 2
fi

pg_restore -d "$TARGET_DB" --no-owner "$DUMP"
psql -d "$TARGET_DB" -c \
  "SELECT (SELECT count(*) FROM app_user) AS users, (SELECT count(*) FROM finding) AS findings;"
echo "restore drill complete for $TARGET_DB"
