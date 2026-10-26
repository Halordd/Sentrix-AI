# SENTRIX — local security-operations demo

SENTRIX is a local-only, five-VM graduation project. It demonstrates an
authorized security-engagement workflow with a FastAPI backend, PostgreSQL,
a mock AI service, a queue worker, an isolated lab VM, and an API-backed UI.

**Local demo only.** No production, shared-tenant, or external-target use is
approved.

## Repository layout

| Folder | Canonical content |
|---|---|
| [`frontend/`](frontend/README.md) | UI, login page, API adapter, static server, Node tests, browser smoke tests |
| [`backend/`](backend/README.md) | FastAPI app, tests, worker, AI mock service, systemd/nginx deployment files |
| [`database/`](database/README.md) | PostgreSQL schema, migrations, seed manifest/seed script, DB operations |
| [`lab/`](lab/README.md) | isolated Juice Shop lab reproduction |
| [`docs/`](docs/phase2/README.md) | Phase 2 specifications, decision records, governance records |
| [`.scratch/`](.scratch/) | Milestone ticket boards (M1–M6 and artifact authorization) |

Architecture diagram: [`FLOWCHART.md`](FLOWCHART.md)

Per-VM source distribution and runtime paths: [`DEPLOYMENT.md`](DEPLOYMENT.md)

One-command source sync:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\sync-source.ps1
```

## Local topology

| VM | Role | APP / LAB | NAT |
|---|---|---|---|
| VM01 `sentrix-app` | Nginx, UI, FastAPI | `10.20.10.10` | `192.168.213.130` |
| VM02 `sentrix-data` | PostgreSQL 16 | `10.20.10.20` | `.131` |
| VM03 `sentrix-ai` | AI mock service | `10.20.10.30` | `.132` |
| VM04 `sentrix-worker` | queue worker | `10.20.10.40` / LAB `10.20.20.10` | `.133` |
| VM05 `sentrix-lab` | isolated Juice Shop + WebGoat | `10.20.20.20` | none |

## Quick commands

### Backend tests

On VM01:

```bash
cd ~/sentrix-backend
venv/bin/pytest -q
```

Latest verified result: **59 passed**.

### Frontend local server

```bash
cd frontend
npm run dev          # http://127.0.0.1:3000
npm test
```

### Browser smoke against the deployed UI

```bash
cd frontend
node scripts/ui-smoke.mjs
```

### Database backup / verification

On VM01:

```bash
~/sentrix-m2/backup.sh
~/sentrix-m2/verify_backup.sh ~/sentrix-backups/<dump>
```

Current schema has **31 tables** (25 baseline + `artifact` + shared auth + automation queue/execution); the seed
fixture remains **51 rows**.

## Deployed endpoints

| URL | Purpose |
|---|---|
| `http://10.20.10.10/` | UI |
| `https://10.20.10.10/` | CA-signed local TLS UI |
| `http://10.20.10.10/api/v1/` | API through Nginx |
| `http://10.20.10.30:8000/health` | existing AI service |
| `http://10.20.10.30:8001/health` | mock inference service |
| `http://10.20.20.20:3000/` | Juice Shop lab |

Local demo credentials:

```text
maya@sentrix.local / sentrix-demo     # ANALYST
admin@sentrix.local / admin-demo      # ADMIN
```

## Security posture

- Bearer-token auth with PBKDF2 password hashes.
- `ANALYST`/`ADMIN` write gate; project membership enforcement.
- Append-only audit/status history; `sentrix_app` is least-privileged.
- Rate limiting and token revocation support optional shared PostgreSQL state (`SENTRIX_SHARED_AUTH=1`); otherwise process-local.
- Worker claims jobs with `FOR UPDATE SKIP LOCKED`; heartbeat/recovery.
- Worker systemd sandbox: **1.6 OK** exposure score.
- VM04 egress allowlist: API, LAB, DNS, loopback; default outgoing deny.
- Self-signed TLS on VM01; MFA/SSO remain out of local scope.
- Artifact upload/download is project-scoped through `artifact` metadata.

## Governance records

| Milestone | Record |
|---|---|
| M1 | [`docs/phase2/12-m1-governance-record.md`](docs/phase2/12-m1-governance-record.md) |
| M2 | [`docs/phase2/14-m2-governance-record.md`](docs/phase2/14-m2-governance-record.md) |
| M3 | [`docs/phase2/15-m3-governance-record.md`](docs/phase2/15-m3-governance-record.md) |
| M4 | [`docs/phase2/16-m4-governance-record.md`](docs/phase2/16-m4-governance-record.md) |
| M5 | [`docs/phase2/21-m5-governance-record.md`](docs/phase2/21-m5-governance-record.md) |
| M6 | [`docs/phase2/18-m6-governance-record.md`](docs/phase2/18-m6-governance-record.md) |
| M7 | [`docs/phase2/22-m7-experiment-record.md`](docs/phase2/22-m7-experiment-record.md) |\n| L3-C | [`docs/phase2/26-l3-conditional-automation.md`](docs/phase2/26-l3-conditional-automation.md) |\n| GNN status | [`docs/phase2/27-gnn-implementation-status.md`](docs/phase2/27-gnn-implementation-status.md) |\n| GNN run | [`docs/phase2/29-gnn-improvement-run.md`](docs/phase2/29-gnn-improvement-run.md) |\n| Web GNN redesign | [`docs/phase2/31-gnn-web-api-redesign.md`](docs/phase2/31-gnn-web-api-redesign.md) |\n| Web corpus | [`docs/phase2/32-web-corpus.md`](docs/phase2/32-web-corpus.md) |\n| Web GNN run | [`docs/phase2/33-web-gnn-run.md`](docs/phase2/33-web-gnn-run.md) |\n| Web GNN 5-seed/ablation | [`docs/phase2/34-web-gnn-5seed-ablation.md`](docs/phase2/34-web-gnn-5seed-ablation.md) |\n| Web GNN 100-record run | [`docs/phase2/35-web-gnn-100-run.md`](docs/phase2/35-web-gnn-100-run.md) |\n| Web GNN external/calibration | [`docs/phase2/36-web-gnn-external-calibration.md`](docs/phase2/36-web-gnn-external-calibration.md) |\n| Web GNN calibration compare | [`docs/phase2/37-web-gnn-calibration.md`](docs/phase2/37-web-gnn-calibration.md) |\n| WebGoat provisioning status | [`docs/phase2/38-webgoat-provisioning.md`](docs/phase2/38-webgoat-provisioning.md) |\n| WebGoat batch 3 | [`docs/phase2/39-webgoat-batch3.md`](docs/phase2/39-webgoat-batch3.md) |\n| WebGoat external result | [`docs/phase2/40-webgoat-external-result.md`](docs/phase2/40-webgoat-external-result.md) |\n| Corpus project import | [`docs/phase2/41-corpus-project-import.md`](docs/phase2/41-corpus-project-import.md) |\n| Corpus pilot UI | [`docs/phase2/42-corpus-pilot-ui.md`](docs/phase2/42-corpus-pilot-ui.md) |\n| WebGoat calibration holdout | [`docs/phase2/43-webgoat-calibration-holdout.md`](docs/phase2/43-webgoat-calibration-holdout.md) |
| X-01 | [`docs/phase2/20-x01-frontend-change-approval-request.md`](docs/phase2/20-x01-frontend-change-approval-request.md) |

M5 is accepted for the local demo; production remains unapproved.

## Known limitations

- No production approval, trusted TLS chain, MFA/SSO, or shared rate-limit store.
- Legacy `PATCH /findings/{id}/status` remains on the backend but the UI uses
  `/transitions`.
- Artifact upload/download is available from the finding detail modal.
- The AI inference path is a deterministic mock.
- The demo password remains documented for local use.
