# SENTRIX — Web GNN external batch validation + calibration

| Field | Value |
|---|---|
| Document ID | `SENTRIX-WEB-GNN-RUN-004` |
| Date | 2026-10-26 |
| Dataset | 101 records, 40 positive |
| Validation | train batch 1 → test batch 2, and reverse |
| Calibration | temperature scaling on training-batch holdout |
| Status | Not calibrated enough; score not imported |

## Results

### Train batch 1 → test batch 2

```json
{
  "precision": 0.5909,
  "recall": 0.65,
  "f1": 0.619,
  "accuracy": 0.6098,
  "prAuc": 0.7167,
  "tp": 13,
  "fp": 9,
  "fn": 7,
  "tn": 12,
  "ece": 0.3577,
  "brier": 0.3234,
  "temperature": 0.9182
}
```

### Train batch 2 → test batch 1

```json
{
  "precision": 0.4348,
  "recall": 1.0,
  "f1": 0.6061,
  "accuracy": 0.675,
  "prAuc": 0.8833,
  "tp": 10,
  "fp": 13,
  "fn": 0,
  "tn": 17,
  "ece": 0.3218,
  "brier": 0.3196,
  "temperature": 0.2238
}
```

## Interpretation

- Cross-batch F1 is around **0.61**, much lower than the random-split 5-seed
  mean (`0.6758` full / `0.7935` no-endpoint).
- One direction has recall 1.0 but precision 0.4348; the other has better
  precision but recall 0.65. The model is unstable across batches.
- ECE around **0.32–0.36** is poor. Temperature scaling did not fix it.
- The model is not calibrated and not ready to produce production scores.

## Conclusion

Do **not** import scores into `automation_candidate` yet.

Reasons:

1. Cross-batch F1 ~0.61.
2. ECE ~0.32–0.36.
3. Only two batches from one lab.
4. No independent second lab.
5. Corpus findings still have no valid `finding.id` mapping into SENTRIX.

## Artifacts

```text
backend/training/web_graph/evaluate_web_gnn.py
backend/training/web_graph/web_external_calibration.json
~/sentrix-gnn/src/web_external_calibration.json
```

## Next

1. Get a second independent lab/corpus.
2. Build a real calibration set (not 20% of a small batch).
3. Compare Platt/isotonic/temperature.
4. Only then consider score import.
