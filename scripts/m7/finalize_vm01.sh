#!/usr/bin/env bash
# Run on VM01 as root/sudo after the frontend and API unit are staged in
# /home/sentrixadmin/sentrix-web and /home/sentrixadmin/sentrix-backend.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "run with sudo on VM01" >&2
  exit 2
fi

WEB_SRC=/home/sentrixadmin/sentrix-web
WEB_DST=/var/www/sentrix
API_SRC=/home/sentrixadmin/sentrix-backend

install -m 644 "$WEB_SRC/app.js" "$WEB_DST/app.js"
install -m 644 "$WEB_SRC/api.js" "$WEB_DST/api.js"
install -m 644 "$WEB_SRC/repository.js" "$WEB_DST/repository.js"
install -m 644 "$WEB_SRC/apiRepository.js" "$WEB_DST/apiRepository.js"

install -m 644 "$API_SRC/sentrix-api.service" /etc/systemd/system/sentrix-api.service

# Apply hardened nginx path policy if staged.
if [[ -f /home/sentrixadmin/sentrix-tls/nginx.sentrix.conf ]]; then
  install -m 644 /home/sentrixadmin/sentrix-tls/nginx.sentrix.conf /etc/nginx/sites-available/sentrix
fi
if [[ -f /home/sentrixadmin/sentrix-tls/nginx.sentrix-tls.conf ]]; then
  install -m 644 /home/sentrixadmin/sentrix-tls/nginx.sentrix-tls.conf /etc/nginx/sites-available/sentrix-tls
fi
nginx -t
systemctl reload nginx

systemctl daemon-reload
systemctl restart sentrix-api

# Give the service a moment, then verify the API and the M7 evaluation record.
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

sudo -u sentrixadmin bash -lc "cd $API_SRC && venv/bin/python training/evaluate.py"
sudo -u sentrixadmin bash -lc "cd $API_SRC && venv/bin/python training/evaluate.py --verify"
sudo -u sentrixadmin bash -lc "cd $API_SRC && venv/bin/pytest -q"

echo "frontend + API deployed; M7 evaluation written; tests completed"
