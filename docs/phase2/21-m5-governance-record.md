# SENTRIX M5 — Frontend Migration Governance & Acceptance Record

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M5-GOV-001` |
| Version | 1.0 |
| Date | 2026-10-26 (Asia/Saigon) |
| Scope | Local demo frontend only |
| Decision | **ACCEPTED — LOCAL DEMO ONLY** |
| X-01 | **APPROVED** |
| Production use | **NOT APPROVED** |
| External targets | **NOT APPROVED** |

## 1. Accepted scope

M5 moves the UI behind a repository seam, replaces the legacy status write with
`/transitions`, polls asynchronous scan runs, aligns verification and CSV export
with the API, and adds browser parity checks.

## 2. Evidence

| Control | Result |
|---|---|
| X-01 | approved local demo on 2026-10-26 |
| Repository seam | `repository.js` + `apiRepository.js`; API default, `?repo=memory` fallback |
| Adapter bug | Proxy `then` made the API repo thenable and silently fell back; fixed |
| Transitions | UI uses `POST /findings/{id}/transitions`; no `/status` calls |
| Forbidden transition | UI no longer cycles `In Progress → Resolved` |
| Scan polling | UI polls `GET /scans/{id}` until Completed/Failed; finding refresh |
| Verification | one `POST /remediations/{id}/verify`; applies `findingStatus` |
| CSV export | API-backed bytes match domain format and quote escaping |
| Backend tests | **49 passed** |
| Frontend tests | 31 pass, 1 skipped (EPERM symlink), 0 fail |
| Browser parity (memory) | **13/13 passed** |
| Browser parity (API, deployed) | **14/14 passed** |
| Off-origin requests | zero; all requests same-origin |
| Uncaught browser errors | zero |

## 3. Conditions

1. Frontend runtime files must be copied to `/var/www/sentrix` after source
   changes; the running UI does not read `~/sentrix-src` directly.
2. Deployed API suite passes 14/14 and deployed memory suite passes 13/13; keep the nginx hidden-path deny config in place and re-run both after frontend changes:
   `browser-check.mjs` (memory, 13) and `browser-api-check.mjs` (API, 14).
3. The API browser suite is read-only against seed data; write workflows are
   covered by backend/frontend tests.
4. Legacy `PATCH /findings/{id}/status` remains on the backend for compatibility
   but is no longer called by the UI; gate/remove it later.
5. Local demo only: no production, external targets, shared tenancy, MFA/SSO,
   or trusted TLS chain.
6. Re-run the full backend suite and browser checks after auth, transition, or
   adapter changes.

## 4. Residual risks

- CSV export is generated client-side from the bootstrap snapshot; no server
  export endpoint and no export audit event.
- Optimistic UI updates reconcile only after the API response; a reload is the
  source of truth.
- Browser API checks do not exercise destructive writes; those remain covered
  by API tests.
- Artifact upload has no UI.
- `/transitions` and verification require project membership; seeded demo
  accounts are documented for local use only.

## 5. Approval

The project owner approved X-01 and accepted M5 for the local demo, subject to
the runtime-copy and re-verification conditions above. Production remains
unapproved.
