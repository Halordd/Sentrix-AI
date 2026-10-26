# Ticket 01 — finding status transition

## Scope

`PATCH /api/v1/findings/{finding_id}/status`

## Behaviour

- Accept one of `NEW`, `CONFIRMED`, `IN_PROGRESS`, `RESOLVED`, `REOPENED`,
  `ACCEPTED_RISK`, `FALSE_POSITIVE` as the next status.
- Read the current finding as `sentrix_app`.
- Update `finding.status` and `updated_at`.
- Insert one `finding_status_event` row with `from_status`, `to_status`,
  actor `user-maya`, and reason.
- Return the updated finding.
- No audit-event insert in this ticket.

## Acceptance

- 200 with the new status.
- `finding_status_event` count increments by one.
- Invalid status returns 422/400.
- Unknown finding returns 404.
- Tracer rows removed after the test; seed counts restored.
