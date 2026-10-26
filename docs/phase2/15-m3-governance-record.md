# SENTRIX M3 — Local Governance & Acceptance Record

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M3-GOV-001` |
| Version | 1.0 |
| Date | 2026-10-23 (Asia/Saigon) |
| Scope | Five local VMware VMs only |
| Decision | **ACCEPTED — LOCAL DEMO ONLY** |
| Production use | **NOT APPROVED** |
| External targets | **NOT APPROVED** |
| Decision owner | SENTRIX project owner (local operator) |

## 1. Accepted scope

M3 adds explicit finding transitions, append-only audit for writes, scan and
verification state guards, project membership, and ADMIN user provisioning. It
does not approve production use or external scanning.

## 2. Evidence

| Check | Result |
|---|---|
| Auth API + login | 200 |
| Transition matrix tests | 7 passed |
| Scan run guard | completed scan → 409 |
| Verification state guard | CONFIRMED finding → 409 |
| Membership flow | add 201, duplicate 409, role 200, last-owner 409, delete 204 |
| Provisioning flow | create 201, patch 200; admin credentials local-only |
| Audit events | project, target, scan, analysis, remediation, verification, report, finding transition, membership, user |
| Seed after tests | users 5, members 3, audits 2, findings 3 |
| Full pytest | **19 passed** |

## 3. Decisions

1. M3 is accepted for local demo use.
2. Project membership and provisioning are API-only; no UI in the MVP.
3. `sentrix_app` received `DELETE` on `project_member` only, for EP-48.
4. Audit rows are append-only and actor-attributed.
5. Demo credentials remain local-only.

## 4. Known gaps and conditions

1. The legacy `PATCH /findings/{id}/status` endpoint still bypasses the M3
   transition matrix and is still used by the UI. Remove or gate it before
   expanding scope; M5 must move the UI to `/transitions`.
2. Optimistic locking (`If-Match`) and idempotency keys are not implemented.
3. Audit `request_id` is the literal `api`; denied authorization attempts are
   not audited.
4. The mutation suite covers one full workflow, not the entire AT-3 matrix.
5. No auth rate limiting, token revocation, or auth-event audit.
6. The demo scanner/inference are hard-coded in the API; M4 port extraction is
   required before adapter conformance.
7. Production/external use remains unapproved.

## 5. Approval

The project owner reviewed M3 evidence and accepted it for the local demo,
subject to the gaps above. M4 planning may proceed locally; production use
remains unapproved.
