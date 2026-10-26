#!/usr/bin/env bash
# Restore the lab Juice Shop container from a snapshot created by snapshot_juice.sh.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <snapshot-image>" >&2
  exit 2
fi
SNAPSHOT="$1"
CONTAINER="${CONTAINER:-sentrix-juice-shop}"

docker image inspect "$SNAPSHOT" >/dev/null
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" --restart unless-stopped --network host "$SNAPSHOT" >/dev/null

echo "restored $CONTAINER from $SNAPSHOT"
