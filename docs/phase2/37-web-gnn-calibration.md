> **Superseded metrics:** see [44-code-review-fixes.md](44-code-review-fixes.md).

# SENTRIX — Calibration comparison

| Field | Value |
|---|---|
| Document ID | `SENTRIX-WEB-GNN-RUN-005` |
| Date | 2026-10-26 |
| Dataset | 101 records, 40 positive |
| Calibration set | 8–9 records per direction |
| Methods | uncalibrated, temperature, Platt, isotonic |
| Status | No method improved calibration; score not imported |

## Results

### Train batch 1 → test batch 2

| Method | F1 | ECE | Brier |
|---|---:|---:|---:|
| uncalibrated | 0.6047 | **0.2001** | **0.2447** |
| temperature | 0.6047 | 0.2330 | 0.2732 |
| Platt | 0.6122 | 0.4495 | 0.4354 |
| isotonic | 0.6122 | 0.2709 | 0.2885 |

### Train batch 2 → test batch 1

| Method | F1 | ECE | Brier |
|---|---:|---:|---:|
| uncalibrated | 0.6061 | **0.1978** | **0.1935** |
| temperature | 0.6061 | 0.3098 | 0.3121 |
| Platt | 0.6061 | 0.3245 | 0.3244 |
| isotonic | 0.6061 | 0.3041 | 0.3055 |

## Interpretation

- Uncalibrated probabilities had the **best** ECE/Brier in both directions.
- Temperature, Platt and isotonic all **made calibration worse**.
- The calibration set is only 8–9 records, so all post-hoc calibrators overfit.
- No calibration method should be adopted from this run.

This is a negative result: with a tiny calibration set, post-hoc calibration is not
justified.

## Artifacts

```text
backend/training/web_graph/calibrate_web_gnn.py
backend/training/web_graph/web_calibration_compare.json
~/sentrix-gnn/src/web_calibration_compare.json
```

## Consequences

Do not import score:

- cross-batch F1 ~0.61;
- no calibration method improved ECE;
- calibration set too small;
- no valid DB mapping for corpus findings;
- no second independent lab.

## Next

1. Build a proper calibration set (100+ records).
2. Repeat on a second lab.
3. Try calibration again only when the set is large enough.
4. Then decide whether the model is fit for candidate ranking.
