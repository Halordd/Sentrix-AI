# SENTRIX — WebGoat calibration holdout

| Field | Value |
|---|---|
| Document ID | `SENTRIX-WEB-GNN-RUN-007` |
| Date | 2026-10-26 |
| Calibration | 20 WebGoat records per split (12 pos / 8 neg) |
| Test | 20 WebGoat records per split |
| Splits | 5 |
| Status | Pilot only; canonical scores unchanged |

## Results

Mean over 5 stratified splits:

| Method | F1 mean | F1 std | ECE mean | ECE std | Brier mean |
|---|---:|---:|---:|---:|---:|
| uncalibrated | 0.0841 | 0.0691 | 0.1773 | 0.0329 | 0.2579 |
| temperature | 0.0841 | 0.0691 | 0.1500 | 0.0316 | 0.2500 |
| Platt | 0.7849 | 0.0222 | 0.2547 | 0.1306 | 0.2460 |
| isotonic | 0.8339 | 0.0215 | **0.1336** | 0.1277 | **0.1899** |

## Interpretation

- With 20 calibration records, isotonic had the best ECE and Brier, and
  temperature slightly improved ECE over uncalibrated.
- F1 changes across methods are dominated by the 0.5 threshold shift, not by
  ranking changes. Temperature and isotonic are monotonic; ranking is unchanged.
- ECE std is high; 20 calibration records is still small.
- This is **not independent** validation: calibration and test are two halves of
  the same WebGoat batch.

## Decision

Do **not** update the canonical `corpus_pilot.candidate.score` yet.

Reasons:

- calibration set still small;
- calibration and test are from the same lab;
- no independent calibration lab;
- F1 is threshold-sensitive;
- canonical data remains explicitly `pilot-uncalibrated`.

## Artifacts

```text
backend/training/web_graph/calibration_webgoat_holdout.py
backend/training/web_graph/web_calibration_webgoat_holdout.json
~/sentrix-gnn/src/web_calibration_webgoat_holdout.json
```

## Next

1. Collect a calibration set from a third independent lab.
2. Freeze a calibrator trained only on that set.
3. Re-score to a separate `candidate_calibrated` table, not overwrite pilot scores.
4. Keep both labels visible.
