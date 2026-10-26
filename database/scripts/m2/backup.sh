#!/usr/bin/env bash
set -euo pipefail

DB_HOST="${SENTRIX_DB_HOST:-10.20.10.20}"
DB_USER="${SENTRIX_DB_USER:-sentrix_migrator}"
DB_NAME="${SENTRIX_DB_NAME:-sentrix}"
BACKUP_DIR="${SENTRIX_BACKUP_DIR:-$HOME/sentrix-backups}"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump="$BACKUP_DIR/sentrix-$stamp.dump"
checksum="$dump.sha256"

pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -Fc -f "$dump"
sha256sum "$dump" > "$checksum"
chmod 600 "$dump" "$checksum"

pg_restore --list "$dump" > "$dump.list"
tables="$(grep -c 'TABLE DATA' "$dump.list" || true)"
echo "backup=$dump"
echo "tables_with_data=$tables"
echo "sha256=$(cut -d' ' -f1 "$checksum")"
