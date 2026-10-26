# SENTRIX M6 workspace

Goal: harden the local demo and make asynchronous execution safe before any
shared or production-like use.

## Scope and guardrails

- Local-only; no external target or production authorization.
- No schema change without a recorded migration.
- Worker must claim work atomically; two workers must never execute one run.
- Secrets never enter API responses, logs, or the frontend bundle.
- Artifact downloads, if exposed, are authenticated and non-inline.

## Tickets

| Ticket | Scope | Status |
|---|---|---|
| M6-01 | Worker claim endpoint using `FOR UPDATE SKIP LOCKED`; heartbeat/recovery | **done — stale-run recovery test passes** |
| M6-02 | Worker/systemd isolation: non-root, read-only home, no ports, resource limits | **done — security score 1.6 OK** |
| M6-03 | Egress allowlist for VM04 LAB; deny other destinations | **done — applied and worker idle** |
| M6-04 | Authenticated artifact download, `Content-Disposition`, no inline HTML/SVG | **done** |
| M6-05 | Rate limiting, token revocation, auth-event audit | **done — shared-state option; login-failure/logout audit** |
| M6-06 | DB least privilege review, secret redaction, static ACL checks | **done** |
| M6-07 | Security suite + concurrency/race tests | **done — 46 passed** |
| M6-08 | M6 governance | **accepted — local demo only** |

## Current baseline

- Bearer token auth, PBKDF2, ANALYST/ADMIN write gate.
- Audit for M3 mutations.
- Worker currently polls `/api/v1/bootstrap` and calls `/scans/{id}/run`; it is
  not yet an atomic claim worker.
- HBA duplicate removed; one migrator rule remains.
- Backup verified; restore drill passed.
- No rate limit, token revocation, or auth-event audit.
- No egress allowlist test; no artifact download endpoint.
- UFW: APP 80; AI 8001 from VM01; LAB 3000 from LAB/.1.

## Current evidence

- `POST /api/v1/worker/claims` uses `FOR UPDATE OF j SKIP LOCKED` and refuses
  jobs with an active PENDING/RUNNING run.
- Two claim calls on one queued scan: first 200, second 204.
- `POST /api/v1/worker/claims/{runId}/heartbeat` updates an active run.
- `POST /api/v1/worker/recover` exists for stale PENDING/RUNNING runs.
- Queued claim → `/scans/{id}/run` completes the claimed PENDING run without
  creating a duplicate attempt.
- Worker `real_worker.py` now claims via the endpoint, heartbeats, then runs.
- Full suite: **35 passed**; seed after tests: scan_job 3, scan_run 3,
  finding 3, audit 2.
- Hardened worker unit adds `ProtectSystem=strict`, `CapabilityBoundingSet=`,
  `ProtectProc=invisible`, syscall/address-family restrictions, and memory/CPU
  limits. `systemd-analyze verify` accepts it.
- Egress allowlist script permits only API `10.20.10.10:80`, LAB
  `10.20.20.20:3000`, loopback, and DNS; rollback script restores outgoing.
- Rate limiter: 600 API req/min per client, 60 login req/min; 429 + Retry-After.
- Token revocation: logout adds the token fingerprint to an shared-state denylist;
  subsequent `/me` returns 401.
- Auth audit records login SUCCESS/DENIED and logout SUCCESS; tests clean
  `auth.*` rows so the seed oracle remains stable.
- Artifact download is authenticated, octet-stream, attachment, nosniff;
  unknown keys return 404; project ownership is enforced via the `artifact`
  metadata table (cross-project upload 404, evidence mismatch 422).
- Full suite: **49 passed** after login-success audit and stale-run recovery.
- Backup structure is now **31 tables** and verification passes.
- M6-06: least-privilege audit confirms schema CREATE false, DELETE only on
  `project_member`, no UPDATE/DELETE on append-only tables; API payloads and
  frontend bundle contain no secret material; `.env` and `.pgpass` are `600`.
- M6-07: security suite **49 passed**, including privilege and secret tests.
- M6-02 installed on VM04: `ProtectSystem=strict`, empty capability set,
  `NoNewPrivileges`, 256M memory cap, address-family restriction; security
  score **1.6 OK**; worker active and idle.
- M6-03 egress allowlist applied on VM04: loopback, API `10.20.10.10:80`,
  LAB `10.20.20.20:3000`, DNS; default outgoing deny. Worker remained
  authenticated and idle, and VM04 reached API `/health`.
- Optional TLS setup is staged in `scripts/m6/enable_local_tls.sh` and
  `deploy/nginx.sentrix-tls.conf`; **applied** as a CA-signed listener on
  VM01 `443`; UI 200 and API 401 responses verified over TLS.
- Residual-risk plan: `docs/phase2/19-m6-residual-risk-plan.md`.
- M6-08 governance: local acceptance recorded in
  `docs/phase2/18-m6-governance-record.md`.


## Acceptance anchors

From `06-migration-and-acceptance.md`:

- AT-6.1 two workers race one PENDING run → exactly one executes.
- AT-6.2 stale heartbeat recovery marks run/job FAILED once.
- AT-6.3 worker non-root, read-only rootfs, caps dropped, no published ports.
- AT-6.4 egress deny; only allowlisted destinations reachable.
- AT-6.5 artifact download auth, attachment, no inline HTML/SVG, traversal/hash.
- AT-6.6 CSRF or token-equivalent unsafe-request protection.
- AT-6.7 app role cannot mutate audit/status history.
- AT-6.8 secret redaction in API/logs/bundle.
- AT-6.10 rate limit returns 429.
- AT-6.11 password storage and inactive-user login rejection.
- AT-6.12 identity/membership audit coverage.
