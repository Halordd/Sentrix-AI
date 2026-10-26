#!/usr/bin/env bash
# Add a local CA-signed TLS listener on VM01 without changing the HTTP site.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "run this script with sudo" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR=/etc/nginx/ssl
mkdir -p "$CERT_DIR"

CA_KEY="$CERT_DIR/sentrix-local-ca.key"
CA_CRT="$CERT_DIR/sentrix-local-ca.crt"
SERVER_KEY="$CERT_DIR/sentrix.key"
SERVER_CRT="$CERT_DIR/sentrix.crt"

if [[ ! -f "$CA_KEY" || ! -f "$CA_CRT" ]]; then
  openssl req -x509 -nodes -newkey rsa:3072 -days 3650 \
    -keyout "$CA_KEY" -out "$CA_CRT" \
    -subj "/CN=SENTRIX Local CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign"
  chmod 600 "$CA_KEY"
  chmod 644 "$CA_CRT"
fi

cat > "$CERT_DIR/sentrix.ext" <<EOF
subjectAltName=IP:10.20.10.10
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EOF

openssl req -nodes -newkey rsa:2048 \
  -keyout "$SERVER_KEY" -out "$CERT_DIR/sentrix.csr" \
  -subj "/CN=10.20.10.10"
openssl x509 -req -in "$CERT_DIR/sentrix.csr" \
  -CA "$CA_CRT" -CAkey "$CA_KEY" -CAcreateserial \
  -out "$SERVER_CRT" -days 825 -sha256 \
  -extfile "$CERT_DIR/sentrix.ext"
chmod 600 "$SERVER_KEY"
chmod 644 "$SERVER_CRT"

install -m 644 "$CA_CRT" /usr/local/share/ca-certificates/sentrix-local-ca.crt
update-ca-certificates

CONFIG="$SCRIPT_DIR/nginx.sentrix-tls.conf"
if [[ ! -f "$CONFIG" ]]; then
  CONFIG="$SCRIPT_DIR/../nginx.sentrix-tls.conf"
fi
cp "$CONFIG" /etc/nginx/sites-available/sentrix-tls
ln -sf /etc/nginx/sites-available/sentrix-tls /etc/nginx/sites-enabled/sentrix-tls

ufw allow 443/tcp
nginx -t
systemctl reload nginx

echo "TLS CA: $CA_CRT"
echo "Server cert: $SERVER_CRT"
echo "VM01 trusts the CA. Import the CA into client trust stores for browser trust."
echo "TLS enabled at https://10.20.10.10/ (CA-signed local)"
