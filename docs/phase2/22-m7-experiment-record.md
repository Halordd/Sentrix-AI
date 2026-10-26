# SENTRIX M7 — Experiment & Evaluation Record

| Field | Value |
|---|---|
| Document ID | `SENTRIX-M7-EXP-001` |
| Date | 2026-10-26 (Asia/Saigon) |
| Status | **ACCEPTED — LOCAL DEMO** |
| Scope | Offline deterministic baseline evaluation |
| Production use | **NOT APPROVED** |

## 1. Decisions

| ID | Decision | Value |
|---|---|---|
| X-03 | Dataset + licence | SENTRIX synthetic baseline fixture, `CC0-1.0` |
| X-04 | Primary metric + tolerance | macro F1; exact reproducibility from fixed fixture and seed |

The fixture is synthetic and labelled for this project. It is not a public
vulnerability corpus and must not be described as one.

## 2. Method

- Dataset: [`backend/training/dataset.jsonl`](../backend/training/dataset.jsonl),
  20 labeled texts.
- Classifier: deterministic keyword baseline
  ([`backend/training/evaluate.py`](../backend/training/evaluate.py)).
- Labels: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
- Metric: macro precision, recall, F1; accuracy also recorded.
- Seed: `42`; environment includes Python/platform/host/script hash/dataset hash.
- Data origin: `MEASURED` — the numbers are computed from the fixed fixture, not
  copied from a mock model.
- Model: `model-sentrix-baseline` / `modelversion-baseline-1.0`, `is_mock=false`,
  stage `CANDIDATE`.

## 3. Current metrics

`--verify` result for the current fixture:

```text
datasetSha256 = 5c1254db85ef7fd3499f6aaac32a150b37d11a774e4aa09278a1f2b54b2b1a57
precision = 0.8611
recall    = 0.8036
f1        = 0.7789
accuracy  = 0.7500
samples   = 20
```

These are baseline measurements, not a claim of production AI quality.

## 4. Database records

Migration: [`database/migrations/002_evaluation_role.sql`](../database/migrations/002_evaluation_role.sql)

Created by `training/evaluate.py`:

- `model-sentrix-baseline`
- `modelversion-baseline-1.0`
- `dataset-baseline`
- `datasetversion-baseline-2026.10`
- `eval-baseline-001` (`MEASURED`, seed 42)

The `sentrix_eval` role is NOLOGIN, with narrow SELECT/INSERT rights; the
training script connects as `sentrix_migrator` and `SET ROLE sentrix_eval`.

## 5. API

```text
GET /api/v1/evaluations
```

Returns each run's `dataOrigin`, metrics, environment, seed, model version and
dataset version. No simulated row is presented as a measurement.

## 6. Conditions

1. `sentrix_eval` role installed on VM02 on 2026-10-26.

   ```bash
   sudo -u postgres psql -d sentrix -f database/migrations/002_evaluation_role.sql
   ```

2. Evaluation run completed (`eval-baseline-001`).

   ```bash
   cd ~/sentrix-backend
   venv/bin/python training/evaluate.py
   ```

3. Verify reproducibly with `--verify`; hash and metrics must match.
4. Promotion to `PRODUCTION` is a separate human decision.
5. No production/UI claim may present mock metrics as measured.
6. This is a local demo evaluation; external datasets/licences are not included.

## 7. Residual risks

- Synthetic fixture is small and not representative of real vulnerability data.
- Rule-based baseline has no trained artifact; `artifact_uri` points at the
  evaluation script, and the model version is explicitly `CANDIDATE`.
- The API test suite does not require the evaluation row; M7 evidence is the
  standalone run + `/evaluations` response.
- No training pipeline or GPU/latency benchmark is included.

## 8. Acceptance

Accepted after the role install, successful measured run, and `/evaluations`
response carrying `dataOrigin: MEASURED` with the recorded metrics. Production
use remains unapproved.
