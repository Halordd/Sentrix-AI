# SENTRIX — Isolated corpus project import

| Field | Value |
|---|---|
| Document ID | `SENTRIX-CORPUS-IMPORT-001` |
| Date | 2026-10-26 |
| Schema | `corpus_pilot` (isolated from `public`) |
| Project | `project-corpus-pilot` |
| Targets | `target-juice-shop`, `target-webgoat` |
| Findings | 141 |
| Candidates | 141 |\n| Verified findings | 38 (14 Juice Shop + 24 WebGoat) |
| Main seed tests | 62 passed |
| Status | Pilot import; not production |

## Why a separate schema

The SENTRIX seed/test fixture expects the public project/finding counts. Importing
141 corpus findings into `public` would break those tests.

Therefore the corpus lives in its own schema:

```text
corpus_pilot.project
corpus_pilot.target
corpus_pilot.finding
corpus_pilot.candidate
```

The public API/schema is untouched.

## Import result

```json
{
  "project": "project-corpus-pilot",
  "findings": 141,
  "candidates": 141,
  "byTarget": {
    "target-juice-shop": 101,
    "target-webgoat": 40
  },
  "scores": 141
}
```

Mapping:

```text
corpus-*  → finding-corpus-*
b2-*      → finding-b2-*
b3-*      → finding-b3-*
```

`source_id` is preserved in `corpus_pilot.finding.source_id`.

## Scores

The score comes from the pilot HeteroConv-SAGE model:

```text
model: HeteroConv-SAGE pilot
scores: 141
min: 0.037449
max: 0.931313
verified findings: 38 (14 Juice Shop + 24 WebGoat)
```

Candidates are queued with `read.response_headers` for CWE-693 and
`read.target_metadata` otherwise. These are **pilot scores**, not calibrated
production probabilities.

## Verify

```sql
SELECT count(*) FROM corpus_pilot.finding;      -- 141
SELECT count(*) FROM corpus_pilot.candidate;    -- 141
SELECT target_id, count(*) FROM corpus_pilot.finding
GROUP BY target_id ORDER BY target_id;
```

Top scores:

```sql
SELECT f.source_id, f.target_id, f.verified, c.score
FROM corpus_pilot.finding f
JOIN corpus_pilot.candidate c ON c.finding_id = f.id
ORDER BY c.score DESC
LIMIT 10;
```

## Read-only API routes

The corpus is exposed through admin-only, read-only routes:

```text
GET /api/v1/corpus/projects
GET /api/v1/corpus/findings?targetId=...&limit=...
GET /api/v1/corpus/candidates?limit=...
```

Every response carries:

```json
{"pilot": true, "scoreLabel": "pilot-uncalibrated"}
```

Manual smoke test on a temporary API process:

```json
{
  "loginStatus": 200,
  "project": {
    "id": "project-corpus-pilot"
  },
  "targets": [
    {"id": "target-juice-shop", "name": "Juice Shop", "type": "WEB", "findings": 101},
    {"id": "target-webgoat", "name": "WebGoat", "type": "WEB", "findings": 40}
  ],
  "pilot": true,
  "scoreLabel": "pilot-uncalibrated"
}
```

## Seed safety

The public schema was not modified.

```text
backend tests: 62 passed
```

## Artifacts

```text
database/corpus/schema.sql
backend/tools/import_web_corpus.py
backend/training/web_graph/web_scores.json
```

## Caveats

- Scores are not calibrated.
- Scores are from a pilot model.
- The corpus project is not exposed through the public SENTRIX API.
- `verified` is the human label, not a production confidence.
- Do not present these candidates as production findings.

## Next

- Add a read-only API route for the corpus project if needed.
- Re-score with a calibrated model only after a larger calibration set.
- Keep `corpus_pilot` out of seed fixtures and public counting tests.
