# Ticket 05 — UI adapter for tickets 01–04

## Scope

`api.js` methods and the existing UI actions.

## Behaviour

- Map UI status labels to enum values.
- Optimistically update local snapshot, then reconcile with the API.
- On API failure, revert the optimistic change and surface a console error.
- Keep the read-only fallback for unimplemented actions.

## Acceptance

- Project, target, scan, run, status, analysis, remediation, verify, and
  report controls all reach the API.
- Browser reload shows persisted rows from `/api/v1/bootstrap`.
