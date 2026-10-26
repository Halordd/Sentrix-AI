# SENTRIX source distribution

The repo is developed on the Windows workspace and synchronized to each VM.
Each VM keeps **the source it needs** under `~/sentrix-src/`, while the running
service uses its stable deployment path. This keeps runtime paths/hardening
stable and still gives every VM a maintainable source copy.

## VM map

| VM | `~/sentrix-src/` contents | Runtime path | Service |
|---|---|---|---|
| VM01 `sentrix-app` | `frontend/`, `backend/`, `database/`, `docs/`, `lab/`, root README/flowchart | `/var/www/sentrix`, `~/sentrix-backend` | `sentrix-api`, nginx |
| VM02 `sentrix-data` | `database/`, `docs/` | PostgreSQL data dir | `postgresql` |
| VM03 `sentrix-ai` | `backend/ai_service`, `deploy/sentrix-ai-mock.service` | `~/sentrix-ai` | `sentrix-ai-mock` |
| VM04 `sentrix-worker` | `backend/worker`, `deploy/` (unit + M6 scripts) | `~/sentrix-worker` | `sentrix-worker-real` |
| VM05 `sentrix-lab` | `lab/` | Docker container | `sentrix-juice-shop` |

## What actually runs

- **VM01 UI**: Nginx serves `/var/www/sentrix`; source is `frontend/`.
- **VM01 API**: systemd runs `~/sentrix-backend/app`; source is `backend/app`.
- **VM02 DB**: PostgreSQL serves the schema; source is `database/`.
- **VM03 AI**: `~/sentrix-ai/main.py`; source is `backend/ai_service/main.py`.
- **VM04 worker**: `~/sentrix-worker/real_worker.py`; source is
  `backend/worker/real_worker.py`.
- **VM05 lab**: Docker image `bkimminich/juice-shop`; source is `lab/`.

So the system already runs without reading `~/sentrix-src/`; the source copy is
for maintenance, rebuilds, and local review. If a runtime file changes, copy it
to the runtime path and restart the service.

## Sync from Windows

Use the one-command sync script:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\sync-source.ps1
```

Limit it to selected VMs:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\sync-source.ps1 -Only VM01,VM04
```

Preview commands without copying:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\sync-source.ps1 -DryRun
```

Manual equivalent:

```powershell
# VM01 full source
scp -i $HOME\.ssh\sentrix_m1_vm01_ed25519 -r `
  frontend backend database docs lab README.md FLOWCHART.md `
  sentrixadmin@10.20.10.10:~/sentrix-src/

# VM02 database
scp -i $HOME\.ssh\sentrix_m1_vm02_ed25519 -r `
  database docs README.md FLOWCHART.md `
  sentrixadmin@10.20.10.20:~/sentrix-src/

# VM03 AI
scp -i $HOME\.ssh\sentrix_m1_vm03_ed25519 -r `
  backend/ai_service backend/deploy/sentrix-ai-mock.service `
  sentrixadmin@10.20.10.30:~/sentrix-src/

# VM04 worker
scp -i $HOME\.ssh\sentrix_m1_vm04_ed25519 -r `
  backend/worker backend/deploy `
  sentrixadmin@10.20.10.40:~/sentrix-src/

# VM05 lab
scp -i $HOME\.ssh\sentrix_m1_vm05_ed25519 -r `
  lab README.md FLOWCHART.md `
  sentrixadmin@10.20.20.20:~/sentrix-src/
```

## Deploy changed frontend

```bash
sudo cp ~/sentrix-web/app.js ~/sentrix-web/api.js \
  ~/sentrix-web/repository.js ~/sentrix-web/apiRepository.js \
  /var/www/sentrix/
```

## Deploy changed backend/worker/AI

```bash
# VM01
sudo systemctl restart sentrix-api

# VM03
sudo systemctl restart sentrix-ai-mock

# VM04
sudo systemctl restart sentrix-worker-real
```

## Verify

```bash
# VM01
cd ~/sentrix-backend && venv/bin/pytest -q
# expected: 47 passed

# Windows
node frontend/scripts/ui-smoke.mjs
```
