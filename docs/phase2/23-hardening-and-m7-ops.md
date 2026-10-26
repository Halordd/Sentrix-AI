# SENTRIX hardening and M7 operation note

| Field | Value |
|---|---|
| Document ID | `SENTRIX-HARDEN-001` |
| Date | 2026-10-26 |
| Scope | Local demo only |

## 1. TLS trust

`backend/deploy/m6/enable_local_tls.sh` now creates a local CA and a CA-signed
server certificate, installs the CA in VM01 trust, and reloads nginx.

```bash
sudo bash ~/sentrix-tls/enable_local_tls.sh
```

Client trust (Windows):

1. Copy `/etc/nginx/ssl/sentrix-local-ca.crt` from VM01.
2. Import it into **Trusted Root Certification Authorities**.
3. Reload/restart the browser.

Browser trust is a client-side step; a self-signed/CA-signed certificate does not
become trusted automatically on other machines.

## 2. Shared rate-limit and revocation state

Migration: `database/migrations/003_shared_auth_state.sql`.

Tables:

- `revoked_token` (SHA-256 fingerprint, expiry)
- `rate_limit_bucket` (fixed window counters)

Enable with:

```text
SENTRIX_SHARED_AUTH=1
```

The API unit already sets this. Without it, the original in-memory limiter and
denylist are used. The shared path was tested with the full 49-test suite.

## 3. Artifact UI

Finding detail now has:

- **Upload artifact** — raw file upload with `X-Project-Id`; max 10 MiB.
- **Download &lt;sha&gt;** — authenticated blob download from the project-scoped
  artifact endpoint.

The project comes from the finding; download is allowed only to project members.

## 4. M7 evaluation

See [`22-m7-experiment-record.md`](22-m7-experiment-record.md).

Completed operator step:

```bash
sudo bash ~/sentrix-m7-role.sh   # on VM02
cd ~/sentrix-backend
venv/bin/python training/evaluate.py
```

Then verify:

```bash
venv/bin/python training/evaluate.py --verify
curl -s -H "Authorization: Bearer <token>" http://10.20.10.10/api/v1/evaluations
```

## 5. Browser checks

Latest source (before runtime copy):

```text
memory source: 13/13 passed
API deployed:  14/14 passed
memory deployed: 13/13 after nginx hidden-path deny
off-origin requests: 0
uncaught exceptions: 0
```

After copying frontend runtime and restarting API, rerun against
`http://10.20.10.10/`.

## 6. Current schema

`28 tables` (25 baseline + `artifact` + `revoked_token` + `rate_limit_bucket`).
Backup verification passed on 2026-10-26.
