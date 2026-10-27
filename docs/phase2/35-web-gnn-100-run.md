> **Superseded metrics:** see [44-code-review-fixes.md](44-code-review-fixes.md).

# SENTRIX — Web GNN 100-record 5-seed run

| Field | Value |
|---|---|
| Document ID | `SENTRIX-WEB-GNN-RUN-003` |
| Date | 2026-10-26 |
| Dataset | 101 records, 40 positive |
| Seeds | 1–5 |
| Model | Heterogeneous SAGE |
| Test | 12 findings per run, 4 positive |
| Status | Pilot; score not imported |

## Results

| Ablation | Test F1 | F1 std | Precision | Recall | PR-AUC |
|---|---:|---:|---:|---:|---:|
| full | 0.6758 | 0.1068 | 0.7656 | 0.6250 | 0.7902 |
| no_graph (MLP) | 0.4611 | 0.0719 | 0.4185 | 0.5250 | 0.6336 |
| no_evidence | 0.4717 | 0.1043 | 0.5152 | 0.4667 | 0.5667 |
| no_endpoint | **0.7935** | 0.1035 | 0.7334 | 0.8667 | 0.8630 |
| no_cwe | 0.6189 | 0.1133 | 0.7587 | 0.5500 | 0.8017 |

Severity baseline precision@K mean: **0.4083**.

## Interpretation

- Full graph still beats no-graph MLP: graph structure contributes.
- Removing evidence or CWE drops F1: both carry signal.
- `no_endpoint` is still the best ablation. One-hot endpoint identity adds
  noise/overfit and should not be used in the final model.
- The larger corpus lowers full F1 versus the 60-record pilot; do not cherry-pick
  the smaller run.

## Caveats

- 101 records / 40 positives is still small.
- Test has only 4 positives per seed.
- One lab, one corpus.
- No calibration or external validation.
- Ablations are only lightly tuned.
- No production integration.

## Artifacts

```text
backend/training/web_graph/web_experiments_v2.json
backend/training/web_graph/web_dataset_v2.json
~/sentrix-gnn/src/web_experiments_v2.json
```

## Score import status

Not imported.

Reason:

1. The corpus findings (`corpus-*`, `b2-*`) live in JSON, not in SENTRIX's
   `finding` table, so there is no valid `finding_id` for
   `automation_candidate`.
2. Importing them into the production SENTRIX project would pollute the seed
   dataset and tests.
3. Calibration and external validation are still missing.

To import later, create a dedicated corpus project/target in a separate database,
map each corpus finding to a real `finding` row, and keep it out of the seed
fixture.
