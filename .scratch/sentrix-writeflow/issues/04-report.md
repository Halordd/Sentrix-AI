# Ticket 04 — report create and publish

## Scope

`POST /api/v1/reports`
`POST /api/v1/reports/{report_id}/publish`

## Behaviour

- Create a `DRAFT` report for a project, optionally tied to a scan.
- Snapshot hash derived from project and title.
- Publish sets `PUBLISHED` and `published_at`.

## Acceptance

- 201 create; 200 publish.
- Report status transition is visible in bootstrap.
- Tracer report removed; seed count returns to 1.
