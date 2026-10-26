# M7 — measured baseline evaluation

This package records a **measured** evaluation of a deterministic rule-based
classifier on a fixed synthetic fixture. It is not a mock-inference claim and
does not train a model.

## Dataset

`dataset.jsonl` — 20 labeled authorization/security finding texts, labels
`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.

- Dataset: `SENTRIX baseline fixture`
- Version: `2026.10`
- Licence: `CC0-1.0`
- Content hash: SHA-256 of `dataset.jsonl`
- Primary metric: **macro F1**
- Reproducibility tolerance: exact (deterministic rules, fixed seed `42`)

## Run

```bash
cd ~/sentrix-backend
venv/bin/python training/evaluate.py --verify   # metrics only, no DB write
venv/bin/python training/evaluate.py            # writes MEASURED evaluation_run
```

The writer requires the `sentrix_eval` role:

```bash
sudo -u postgres psql -d sentrix -f database/migrations/002_evaluation_role.sql
```

The script connects with `SENTRIX_TRAINING_DSN` (default:
`sentrix_migrator@10.20.10.20/sentrix`) and `SET ROLE sentrix_eval`.

## Records written

- `model`: `model-sentrix-baseline` (LOCAL)
- `model_version`: `modelversion-baseline-1.0` (CANDIDATE, is_mock=false)
- `dataset`: `dataset-baseline`
- `dataset_version`: `datasetversion-baseline-2026.10`
- `evaluation_run`: `eval-baseline-001`, `data_origin=MEASURED`, seed 42,
  environment + metrics

## API

```text
GET /api/v1/evaluations
```

Returns metrics, environment, seed, dataset/model versions, and per-row
`dataOrigin`. Simulated rows are never labelled as measurements.

## Limits

- Synthetic fixture, not a production dataset.
- Rule-based baseline, not a trained model.
- Promotion to `PRODUCTION` remains a human action.
- M7 acceptance is conditional on the `sentrix_eval` role install and a recorded
  X-03/X-04 decision.
