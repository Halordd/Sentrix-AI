# SENTRIX backend

FastAPI service, queue worker, mock AI service, and deployment units for the
local SENTRIX demo.

## Contents

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI routes, auth middleware, state transitions, audit |
| `app/auth.py` | PBKDF2 passwords + HMAC bearer tokens + revocation |
| `app/adapters.py` | environment-selected adapter registry |
| `app/demo_scanner.py` | deterministic scanner adapter |
| `app/mock_inference.py` | mock inference adapter |
| `app/artifact_store.py` | content-addressed filesystem store |
| `app/execution.py` | no-shell subprocess backend |
| `app/ports.py` | Scanner/Inference/Artifact/Execution ports |
| `app/bootstrap.py` | read projection for the UI |
| `app/rate_limit.py` | in-memory sliding-window limiter |
| `app/db.py` | SQLAlchemy engine |
| `tests/` | pytest suite |
| `training/` | M7 fixed fixture, deterministic evaluator, metrics |
| `worker/` | atomic claim worker |
| `ai_service/` | AI mock service |
| `deploy/` | systemd units, nginx configs, egress/TLS scripts |

## Run tests

On VM01:

```bash
cd ~/sentrix-backend
venv/bin/pytest -q
```

Latest production result: **47 passed**.

From the repository:

```bash
cd backend
venv/bin/pytest -q       # if a venv exists
```

## Runtime

| Service | Unit | Port |
|---|---|---|
| FastAPI | `sentrix-api.service` | `127.0.0.1:8000` |
| Worker | `sentrix-worker-real.service` | none (outbound) |
| AI mock | `sentrix-ai-mock.service` | `10.20.10.30:8001` |

Nginx on VM01 proxies `/api/` to the API.

## API surface

- `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/me`
- `/api/v1/bootstrap`
- projects, targets, scans, worker claims, findings, analyses, remediations,
  reports, members, users
- `/api/v1/scans/{id}` (latest run + findings for UI polling)
- `/api/v1/artifacts` (project-scoped upload) and
  `/api/v1/artifacts/{sha256}` (project-scoped download)

All `/api/v1/*` except login require a bearer token. Writes require
`ANALYST`/`ADMIN`; membership/provisioning checks apply.

## Worker

```mermaid
flowchart LR
    W[worker] -->|POST /worker/claims| API
    API -->|FOR UPDATE SKIP LOCKED| DB[(PostgreSQL)]
    W -->|heartbeat| API
    W -->|POST /scans/{id}/run| API
    API -->|finding + evidence + audit| DB
```

The worker has a hardened systemd unit (read-only home, empty capability set,
syscall/address-family restrictions, memory/CPU limits) and a VM04 egress
allowlist.

## Security

- Passwords: PBKDF2-SHA256, 210k iterations.
- Tokens: HMAC-signed, 8h TTL, in-memory revocation on logout.
- Rate limits: 600 API/min, 60 login/min per client.
- Least privilege: `sentrix_app` has no DELETE except `project_member`; no
  UPDATE/DELETE on append-only tables.
- Artifacts: `artifact` metadata binds SHA-256 to a project; downloads require
  membership.
- Production/external use is not approved.

## Deploy files

`deploy/nginx.sentrix.conf`, `deploy/nginx.sentrix-tls.conf`,
`deploy/sentrix-api.service`, `deploy/sentrix-worker-real.service`,
`deploy/sentrix-ai-mock.service`, and `deploy/m6/` operational scripts.
