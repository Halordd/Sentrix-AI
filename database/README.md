# SENTRIX database

PostgreSQL schema, seed, migrations, and database operations for the local
SENTRIX demo.

## Contents

| Path | Purpose |
|---|---|
| `schema.sql` | full PostgreSQL 16 schema (31 tables incl. `artifact` and shared auth state) |
| `migrations/001_artifact_metadata.sql` | artifact metadata migration |
| `seed-manifest.json` | deterministic 51-row seed oracle |
| `seed/seed_demo.py` | seed runner (`psycopg`, migrator connection) |
| `scripts/m1/` | schema verification, grants, tracer cleanup |
| `scripts/m2/` | backup/restore, password hashes |
| `scripts/m3/` | membership grants and transition/membership traces |

## Roles

| Role | Purpose |
|---|---|
| `sentrix_migrator` | DDL/seed/backup owner; not used by the API |
| `sentrix_app` | runtime app role; least privilege |
| `postgres` | local peer for restore drill |

`sentrix_app`:

- SELECT/INSERT/UPDATE on mutable tables.
- DELETE only on `project_member`.
- No UPDATE/DELETE on `audit_event`, `finding_status_event`,
  `prompt_template_version`.
- No CREATE on schema `public`.

## Apply schema

```bash
psql -h 10.20.10.20 -U sentrix_migrator -d sentrix -w -f schema.sql
psql -h 10.20.10.20 -U sentrix_migrator -d sentrix -w -f migrations/001_artifact_metadata.sql
```

## Seed

```bash
cd database
python seed/seed_demo.py
```

Expected: **51 rows** across 25 seed-bearing tables; `artifact` is empty.

## Backup / restore

```bash
database/scripts/m2/backup.sh
database/scripts/m2/verify_backup.sh ~/sentrix-backups/<dump>
```

Restore drill uses local peer on VM02 (do not broaden HBA):

```bash
sudo -u postgres createdb -O sentrix_migrator sentrix_restore_test
sudo -u postgres bash database/scripts/m2/restore_local.sh \
  sentrix_restore_test /tmp/<dump>
sudo -u postgres dropdb sentrix_restore_test
```

The current backup verifies **31 tables**.

## Artifact metadata

```sql
artifact (
  sha256      text primary key,
  project_id  text not null references project(id),
  evidence_id text references evidence(id),
  created_by  text not null references app_user(id),
  created_at  timestamptz not null
)
```

The API uploads content, stores it by SHA-256, and binds the key to a project.
Downloads require project membership.

## Documentation

Full data model and specifications remain under
[`docs/phase2/`](../docs/phase2/README.md):

- `03-data-model.md`
- `05-state-transitions.md`
- `06-migration-and-acceptance.md`
- `08-remediation-change-log.md`
