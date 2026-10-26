# SENTRIX M5 workspace

Goal: move the frontend from the current demo adapter to a formal API repository,
with parity against the existing UI workflows.

## Entry gate

**X-01 APPROVED 2026-10-26 — local demo only.** See
`docs/phase2/20-x01-frontend-change-approval-request.md`.

The current UI already contains local demo auth/api changes made while building
M1–M4; M5 must reconcile them into the repository interface and parity tests.

## Tickets

| Ticket | Scope | Status |
|---|---|---|
| M5-00 | Record X-01 frontend-change approval | **done — approved local demo** |
| M5-01 | Define `repository.js` interface + `apiRepository.js` | **done** |
| M5-02 | Move transition UI from legacy `/status` to `/transitions` | **done** |
| M5-03 | Scan run → polling → completed/finding refresh | **done** |
| M5-04 | Verification/remediation flow parity | **done** |
| M5-05 | CSV export byte-parity | **done** |
| M5-06 | Browser parity checks + no off-origin requests | **done — 13/13 memory, 14/14 API** |
| M5-07 | M5 governance | **done — accepted local demo** |

## Known prerequisites

- `/api/v1/auth/login` token flow already exists.
- Legacy `PATCH /findings/{id}/status` is no longer called by the UI; all
  finding transitions use `/api/v1/findings/{id}/transitions`.
- `repository.js` selects API by default and `?repo=memory` for the in-memory
  fallback; `apiRepository.js` is the API adapter entry point.
- No uncaught browser errors, no off-origin requests, no `?repo=api` leak.

## Progress

- M5-01: `repository.js`, `apiRepository.js`; fixed a Proxy `then` bug that made
  the API repository look thenable and silently fall back to memory.
- M5-02: transition UI uses `/transitions`; UI cycle avoids forbidden
  `In Progress → Resolved`.
- M5-03: backend `GET /api/v1/scans/{id}` exposes latest run and findings; UI
  polls until `Completed`/`Failed` and dispatches `sentrix:scan-updated`.
- M5-04: verification uses one `POST /remediations/{id}/verify`; the response
  `findingStatus` is applied to the linked finding; failed verification reverts
  optimistic state.
- M5-05: `exportReportCsv` is implemented in `api.js` and matches the domain
  CSV format (including quoting and evidence fields).
- M5-06: memory browser suite **13/13 passed**; API browser suite **14/14
  passed**, including login/bootstrap, all eight views, CSV export, reload
  persistence, zero off-origin requests, and zero uncaught exceptions.
- Backend suite: **49 passed**. Frontend suite: 31 pass, 1 skipped (EPERM
  symlink), 0 fail.

## Acceptance anchors

From `06-migration-and-acceptance.md`:

- AT-5.1 repository parity against the five `tests/domain.test.js` scenarios.
- AT-5.3 all 13 browser checks pass in API mode.
- AT-5.5 scan run → polling → completed/finding appears.
- AT-5.6 verification flow: one `POST /verifications`, then finding resolved.
- AT-5.8 no off-origin request; API calls only behind the flag.
