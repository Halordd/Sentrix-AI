#!/usr/bin/env bash
set -euo pipefail

DUMP="${1:-}"
if [[ -z "$DUMP" || ! -f "$DUMP" ]]; then
  echo "usage: $0 <dump_file>" >&2
  exit 2
fi

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

pg_restore --list "$DUMP" > "$workdir/list.txt"
data_tables="$(grep -c 'TABLE DATA' "$workdir/list.txt" || true)"
schema_tables="$(grep -c 'TABLE public' "$workdir/list.txt" || true)"

echo "data_tables=$data_tables"
echo "schema_tables=$schema_tables"

if [[ "$data_tables" -ne 31 || "$schema_tables" -ne 31 ]]; then
  echo "backup verification failed: expected 31 tables" >&2
  exit 1
fi
echo "backup verification passed"
