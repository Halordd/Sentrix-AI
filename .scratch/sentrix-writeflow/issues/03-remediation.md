# Ticket 03 — remediation create and verify

## Scope

`POST /api/v1/findings/{finding_id}/remediations`
`POST /api/v1/remediations/{remediation_id}/verify`

## Behaviour

- Create a remediation owned by `user-maya`, status `IN_PROGRESS`.
- Verification inserts a `verification` row and closes the remediation.
- On successful verification, move the finding to `RESOLVED` and append a
  `finding_status_event`.

## Acceptance

- 201 create; 200 verify.
- Remediation status becomes `COMPLETED` with `closed_at`.
- Finding status becomes `RESOLVED`; status event count increments by one.
- Tracer rows removed; seed counts restored.

## Constraint

`finding_status_event` is append-only: INSERT only, never UPDATE/DELETE.
