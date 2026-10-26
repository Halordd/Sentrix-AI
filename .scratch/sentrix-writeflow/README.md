# SENTRIX write workflow workspace

Goal: finish the API-backed workflow so the deployed UI can create and advance
real records instead of only reading the seed.

## Ground rules

- One ticket = one traceable workflow write path.
- Every write runs as `sentrix_app` (runtime role), never as `sentrix_migrator`.
- Append-only tables (`audit_event`, `finding_status_event`,
  `prompt_template_version`) accept INSERT only.
- Each test creates tracer rows and removes them afterward; the seed stays at
  51 rows.
- A ticket is complete only when its endpoint and UI adapter both work.

## Ticket board

| Ticket | Scope | Blocked by | Status |
|---|---|---|---|
| 01 | Finding status transition | — | done |
| 02 | Mock analysis creation | 01 | done |
| 03 | Remediation create/verify | 01 | done |
| 04 | Report create/publish | — | done |
| 05 | UI adapter for tickets 01–04 | 01–04 | done |
| 06 | Worker consumes queued scans | 05 | done |
| 07 | Backend calls VM03 AI | 02 | done |
| 08 | Acceptance tests and seed oracle | 05–07 | done |

## Already complete

- Project create.
- Target create + authorization.
- Scan queue.
- Deterministic simulated scan: run, finding, evidence, status event.
- Ticket 01: `PATCH /api/v1/findings/{id}/status`; verified `CONFIRMED → IN_PROGRESS`, event inserted, seed restored.
- Ticket 02: `POST /api/v1/findings/{id}/analyses`; verified 201 on a finding without a live analysis, tracer removed.
- Ticket 03: `POST /api/v1/findings/{id}/remediations` and `POST /api/v1/remediations/{id}/verify`; verified 201/200, finding resolved, tracer removed.
- Ticket 04: `POST /api/v1/reports` and `POST /api/v1/reports/{id}/publish`; verified 201/200, tracer removed.
- Ticket 05: `api.js` methods for project, target, scan, run, status, analysis, remediation, verify, report, publish.
- Ticket 06: `worker/real_worker.py` polls `/api/v1/bootstrap`, claims `Queued` scans, calls `/scans/{id}/run`; verified end-to-end on VM04, `sentrix-worker-real` active.
- Ticket 07: `ai_service/main.py` exposes `/v1/analyze` on VM03 `8001`; production API returned 201 with model `sentrix-ai-mock`.
- Ticket 08: `scripts/m1/acceptance.py` PASSED; `pytest` 7 passed; `scripts/ui-smoke.mjs` passed 8 views.
- Local M1 acceptance recorded in `docs/phase2/12-m1-governance-record.md`.

## Working order

1. Ticket 01: PATCH finding status, append status event.
2. Ticket 02: POST analysis, fixed mock model/prompt.
3. Ticket 03: POST remediation, POST verification.
4. Ticket 04: POST report, POST publish.
5. Ticket 05: adapter methods and UI feedback.
6. Re-run tracer tests, restore seed counts to 51.
