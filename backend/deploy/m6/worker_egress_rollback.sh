#!/usr/bin/env bash
# Roll back the VM04 worker egress allowlist if the worker loses API access.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "run this script with sudo" >&2
  exit 2
fi

ufw default allow outgoing
ufw reload
ufw status verbose
