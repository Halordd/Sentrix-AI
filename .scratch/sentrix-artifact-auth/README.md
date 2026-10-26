# SENTRIX artifact authorization workspace

Goal: bind content-addressed artifacts to projects and require project
membership for upload/download.

## Ticket

| Field | Value |
|---|---|
| ID | `ART-01` |
| Status | **done — local demo** |
| Migration | `scripts/artifacts/001_artifact_metadata.sql` |

## Schema

`artifact`:

```text
sha256      text primary key  (64 lowercase hex)
project_id  text not null references project(id) on delete cascade
evidence_id text references evidence(id) on delete set null
created_by  text not null references app_user(id)
created_at  timestamptz not null
```

App role: `SELECT, INSERT` only.

## API

### Upload/register

```text
POST /api/v1/artifacts
Headers: X-Project-Id, optional X-Evidence-Id
Body: raw bytes (max 10 MiB)
```

Guards:

- active project
- project membership role `OWNER` or `ANALYST` (ADMIN bypass)
- evidence must belong to the same project
- store is content-addressed by SHA-256
- audit `artifact.registered`

### Download

```text
GET /api/v1/artifacts/{sha256}
```

Guards:

- artifact metadata must exist
- caller must be a project member (ADMIN bypass)
- non-member → 404
- returns `application/octet-stream`, `attachment`, `nosniff`

## Verification

- artifact upload/download test passes
- cross-project upload → 404
- evidence/project mismatch → 422
- unknown key → 404
- artifact row removed by cleanup; seed remains 51
- backup now has 26 tables and verification passes
