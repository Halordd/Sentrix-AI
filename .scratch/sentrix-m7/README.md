# SENTRIX M7 workspace

Goal: reproducible, measured offline evaluation with explicit data provenance.

| Ticket | Scope | Status |
|---|---|---|
| M7-01 | X-03/X-04 decisions + fixed fixture | done |
| M7-02 | Deterministic baseline evaluator + metrics | done |
| M7-03 | `sentrix_eval` role + `evaluation_run` records | **done** |
| M7-04 | `GET /api/v1/evaluations` | done |
| M7-05 | Reproducibility verification and governance | **accepted local demo** |

## Evidence

- Fixture hash: `5c1254db85ef7fd3499f6aaac32a150b37d11a774e4aa09278a1f2b54b2b1a57`
- baseline metrics: precision `0.8611`, recall `0.8036`, F1 `0.7789`,
  accuracy `0.7500` over 20 samples.
- Records: `model-sentrix-baseline`, `modelversion-baseline-1.0`,
  `datasetversion-baseline-2026.10`, `eval-baseline-001`.
- API: `GET /api/v1/evaluations` includes `dataOrigin` per run.

## Completed operator steps

```bash
sudo -u postgres psql -d sentrix -f database/migrations/002_evaluation_role.sql
cd ~/sentrix-backend
venv/bin/python training/evaluate.py
venv/bin/python training/evaluate.py --verify
```

Then confirm `/api/v1/evaluations` includes `eval-baseline-001` with
`dataOrigin: MEASURED`.
