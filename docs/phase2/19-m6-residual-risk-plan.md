# SENTRIX M6 — Residual Risk & Mitigation Plan

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M6-RISK-001` |
| Date | 2026-10-26 (Asia/Saigon) |
| Scope | Local demo; pre-shared-use |

## 1. Resolved in this pass

- **Login success audit:** added `auth.login` SUCCESS event. Tests clean
  `auth.*` rows so the 51-row seed oracle remains stable.
- **Worker stale-run recovery:** automated `test_worker_recovery.py` creates a
  claimed run, ages its heartbeat, calls `/worker/recover`, and asserts run/job
  `FAILED`.
- **Artifact per-project authorization:** implemented with an `artifact`
  metadata table, upload/register endpoint, and project-membership checks.
- **TLS option:** `backend/deploy/m6/enable_local_tls.sh` and
  `backend/deploy/nginx.sentrix-tls.conf` add a CA-signed local HTTPS listener
  without changing HTTP/API/worker paths.

## 2. Shared rate limit and token denylist

Current state can use the PostgreSQL tables `revoked_token` and `rate_limit_bucket` with `SENTRIX_SHARED_AUTH=1`. For multi-process/tenant use:

- Move rate-limit counters to Redis or a small Postgres table.
- Move revoked token fingerprints to a durable table with expiry cleanup.
- Keep the in-memory implementation for the single-process local demo.

## 3. Artifact per-project authorization

**Resolved 2026-10-26.** Added:

- Migration `database/migrations/001_artifact_metadata.sql` with `artifact`
  (`sha256`, `project_id`, `evidence_id`, `created_by`, `created_at`).
- `POST /api/v1/artifacts` raw-body upload with `X-Project-Id`,
  optional `X-Evidence-Id`, project membership (OWNER/ANALYST), active-project
  check, and evidence/project consistency check.
- `GET /api/v1/artifacts/{sha256}` now looks up artifact metadata and requires
  project membership; non-members get 404.
- `artifact` is append-only in practice: app role gets SELECT/INSERT only.
- Tests cover upload/download, cross-project upload 404, wrong-evidence 422,
  and unknown-key 404.

Backup structure is now 26 tables; `verify_backup.sh` updated and a 26-table
backup passed verification.

## 4. TLS / MFA / SSO

- TLS: CA-signed local listener is prepared; browser trust is not.
- MFA and SSO are out of scope for the local demo and require an identity
  provider + session/CSRF design.
- Do not expose the API/UI beyond the local APP network.

## 5. M5 gate (X-01)

M5 cannot be treated as approved until X-01 frontend-change approval is
recorded. The current demo UI already contains local changes; M5 must reconcile
them, not assume approval.

## 6. Recommended order

1. Apply optional TLS if needed for a local demo.
2. Add artifact metadata table + upload/register endpoint before exposing
   artifact download to project members.
3. Add shared rate-limit/revocation store only if running multiple API workers.
4. Record X-01, then start M5.
