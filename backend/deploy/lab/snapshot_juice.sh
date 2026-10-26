#!/usr/bin/env bash
# Snapshot the local Juice Shop container before an L3-C lab run.
set -euo pipefail

CONTAINER="${CONTAINER:-sentrix-juice-shop}"
SNAPSHOT="${1:-sentrix-juice-snapshot-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT="${HOME}/sentrix-lab-snapshots"
mkdir -p "$OUT"

docker inspect "$CONTAINER" > "$OUT/${SNAPSHOT}.json"
docker commit "$CONTAINER" "$SNAPSHOT" >/dev/null
docker image inspect "$SNAPSHOT" --format '{{.Id}}' > "$OUT/${SNAPSHOT}.image"

echo "snapshot=$SNAPSHOT"
echo "metadata=$OUT/${SNAPSHOT}.json"
echo "image=$OUT/${SNAPSHOT}.image"
