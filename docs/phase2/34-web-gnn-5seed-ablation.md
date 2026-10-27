> **Superseded metrics:** see [44-code-review-fixes.md](44-code-review-fixes.md).

# SENTRIX — Web GNN 5-seed + ablation

| Field | Value |
|---|---|
| Document ID | `SENTRIX-WEB-GNN-RUN-002` |
| Date | 2026-10-26 |
| Dataset | 60 records, 20 positive |
| Seeds | 1, 2, 3, 4, 5 |
| Model | Heterogeneous SAGE (HeteroConv) |
| Test | 12 findings per run, 4 positive |
| Status | Pilot; no score import |

## Results

Mean ± population std over 5 seeds:

| Ablation | Test F1 | F1 std | Precision | Recall | PR-AUC |
|---|---:|---:|---:|---:|---:|
| full | 0.7144 | 0.1958 | 0.6767 | 0.8000 | 0.8875 |
| no_graph (MLP) | 0.5290 | 0.1191 | 0.5894 | 0.6500 | 0.6750 |
| no_evidence | 0.4434 | 0.2241 | 0.4191 | 0.5000 | 0.7125 |
| no_endpoint | 0.8089 | 0.0815 | 0.7067 | 0.9500 | 0.9312 |
| no_cwe | 0.4567 | 0.2348 | 0.4391 | 0.5000 | 0.8312 |

Severity baseline precision@4: **0.30** mean.

## Interpretation

- Full graph beats no-graph MLP: graph structure contributes signal.
- Removing evidence or CWE drops F1 sharply: both carry useful context.
- Removing endpoint identity **improves** F1 and lowers variance. The
  one-hot endpoint identity is likely memorizing paths / adding noise.
- The best ablation is `no_endpoint`, not `full`.

This is a real negative result about the endpoint feature, not a reason to hide
the feature.

## Caveats

- 60 records / 20 positives.
- Test has only 4 positives per seed.
- 5 seeds reduce but do not remove small-sample variance.
- One lab, one corpus.
- No external validation.
- Ablations are not hyperparameter-tuned individually.

## Artifacts

```text
backend/training/web_graph/run_web_experiments.py
backend/training/web_graph/web_experiments.json
~/sentrix-gnn/src/web_experiments.json
```

## Corpus expansion status

Target: 100+ records / 40+ positive.

Current:

```text
60 records
20 human-verified positives
```

Not expanded. Additional positives require human review of new evidence. Do not
duplicate records to inflate the count.

## Score import status

Not done. Conditions not met:

- 40+ positive
- larger test set
- calibration
- independent validation
