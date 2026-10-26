# SENTRIX M2 workspace

Goal: make the local M1 demo safe enough to extend: authentication, role
gating, backup/restore, hardening, and complete mutation tests.

## Ground rules

- Local-only. No production or external target is authorized.
- Writes require a bearer token; `VIEWER` tokens are read-only.
- Every mutation test cleans its tracer rows; the seed returns to 51.
- Backups are verified with `pg_restore --list`; restore is tested into a
  separate database, never over `sentrix`.
- Secrets stay in `~/.env` or `/etc`, never in the repo.

## Ticket board

| Ticket | Scope | Status |
|---|---|---|
| M2-01 | Token login + login page | **done** |
| M2-02 | Role gate on writes | **done** |
| M2-03 | Mutation pytest suite | **9 passed** |
| M2-04 | Backup + structural verification | **passed — 25 tables** |
| M2-05 | Restore into scratch DB | **passed** — 5 users / 3 findings; DB dropped |
| M2-06 | Hardening checklist | **done** — SSH exposure accepted for local demo |
| M2-07 | M2 acceptance + governance | **accepted — local demo only** |

## Verification commands

Authenticated tests:

```bash
cd ~/sentrix-backend
venv/bin/pytest -q
```

Authenticated acceptance:

```bash
python3 /tmp/acceptance.py
```

Backup:

```bash
~/sentrix-m2/backup.sh
~/sentrix-m2/verify_backup.sh ~/sentrix-backups/<dump>
```

## Restore drill

TCP restore from VM01 needs a database-specific `pg_hba.conf` rule, which the
current HBA intentionally does not have for scratch databases. Use the local
peer path on VM02 instead:

```bash
# VM02
sudo -u postgres createdb -O sentrix_migrator sentrix_restore_test
sudo -u postgres pg_restore -d sentrix_restore_test --no-owner /tmp/sentrix-restore-drill.dump
sudo -u postgres psql -d sentrix_restore_test -c \
  "SELECT (SELECT count(*) FROM app_user) users, (SELECT count(*) FROM finding) findings;"
sudo -u postgres dropdb sentrix_restore_test
```

The dump is already at `/tmp/sentrix-restore-drill.dump` on VM02.

## Current evidence

- Login: `maya@sentrix.local` → token; no-token bootstrap 401.
- UI smoke: 9 checks passed (overview + 8 views).
- Pytest: 9 passed.
- Acceptance: PASSED.
- Worker: authenticated as Maya and polling.
