# SENTRIX M3 workspace

Goal: turn the write API into an explicit state machine with append-only audit,
then add membership/provisioning and the transition matrix tests.

## Ground rules

- No arbitrary status writes: transitions are named and guarded.
- `RESOLVED` is reachable only through a recorded `VERIFIED` verification.
- Every status change appends exactly one `finding_status_event` and one
  `audit_event`.
- Append-only tables accept INSERT only.
- Mutation tests clean their tracer rows and restore the 51-row seed.

## Tickets

| Ticket | Scope | Status |
|---|---|---|
| M3-01 | Finding transition endpoint + matrix | **done** |
| M3-02 | Audit events for writes | **done** |
| M3-03 | Scan job/run guards | **done** |
| M3-04 | Remediation/verification guards | **done** |
| M3-05 | Membership/provisioning endpoints | **done** |
| M3-06 | Transition matrix tests | **19 passed total suite** |
| M3-07 | M3 governance | **accepted — local demo only** |

## Finding transition matrix

Generic transitions (`POST /api/v1/findings/{id}/transitions`) exclude
`RESOLVED`; resolution is verification-only.

| From | Allowed `to` |
|---|---|
| NEW | CONFIRMED, FALSE_POSITIVE, ACCEPTED_RISK |
| CONFIRMED | ACCEPTED_RISK, FALSE_POSITIVE |
| IN_PROGRESS | REOPENED, ACCEPTED_RISK |
| REOPENED | CONFIRMED, ACCEPTED_RISK, FALSE_POSITIVE |
| RESOLVED | REOPENED |
| ACCEPTED_RISK | REOPENED |
| FALSE_POSITIVE | REOPENED |

`NEW → IN_PROGRESS` goes through remediation creation, not this endpoint.

## Evidence

- `POST /api/v1/findings/{id}/transitions` rejects forbidden pairs with 409.
- `to=RESOLVED` returns `finding.verification_required` (409).
- Missing reason on `ACCEPTED_RISK` returns 422.
- Allowed `CONFIRMED → ACCEPTED_RISK` inserted one status event and one
  `finding.transitioned` audit event; tracer rows were removed.
- `pytest tests/test_transitions.py`: **7 passed** against the auth API.
- Completed scan run guard: `POST /scans/scan-atlas/run` → **409**.
- Verification guard: verifying `task-bola` while its finding is `CONFIRMED`
  → **409**.
- Full suite against latest auth API: **19 passed**.
- Membership flow verified: add user-jon, duplicate 409, role change, last-owner
  guard 409, delete 204.
- Provisioning verified with `admin@sentrix.local / admin-demo`: create user 201,
  patch role 200. Both demo credentials are local-only.
- `GRANT DELETE ON project_member TO sentrix_app` added for EP-48.
- Audit events verified for project, target, scan queue/completion, analysis,
  remediation, verification, report create/publish, finding transition,
  membership and user provisioning; mutation cleanup restores audit count to 2.

