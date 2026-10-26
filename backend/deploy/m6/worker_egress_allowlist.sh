#!/usr/bin/env bash
# Apply the VM04 worker egress allowlist. Run with sudo and review first.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "run this script with sudo" >&2
  exit 2
fi

ufw allow out on lo comment 'SENTRIX worker loopback'
ufw allow out to 10.20.10.10 port 80 proto tcp comment 'SENTRIX API'
ufw allow out to 10.20.20.20 port 3000 proto tcp comment 'SENTRIX LAB'
ufw allow out 53/udp comment 'DNS'
ufw allow out 53/tcp comment 'DNS TCP'
ufw default deny outgoing
ufw reload
ufw status numbered
