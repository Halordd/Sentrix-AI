# SENTRIX — External validation on WebGoat

| Field | Value |
|---|---|
| Document ID | `SENTRIX-WEB-GNN-RUN-006` |
| Date | 2026-10-27 |
| Train | Reviewed Juice Shop records: 46 (14 positive / 32 negative) |
| Test | WebGoat batch 3: 40 records / 24 positive |
| Model | Heterogeneous SAGE |
| Status | Pilot external validation, corrected after review |

## Correction

The earlier version of this document claimed **101 records / 40 positive** and
**F1 0.9091**. Those numbers were not reproducible from the checked-in corpus:
18 records were still `PENDING_HUMAN_REVIEW`, and the dataset had been backfilled
to 40 positives.

The corrected run uses only `HUMAN_VERIFIED` / `HUMAN_REJECTED` labels.

## Result

```json
{
  "trainSize": 20,
  "validationSize": 6,
  "testSize": 40,
  "testPositives": 24,
  "severityBaseline": {
    "k": 24,
    "precisionAtK": 0.625,
    "recallAtK": 0.625,
    "hits": 15
  },
  "uncalibrated": {
    "precision": 0.6471,
    "recall": 0.9167,
    "f1": 0.7586,
    "ece": 0.3563,
    "brier": 0.2916
  },
  "temperature": {
    "precision": 0.6471,
    "recall": 0.9167,
    "f1": 0.7586,
    "ece": 0.347,
    "brier": 0.2754
  },
  "platt": {
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0
  },
  "isotonic": {
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0
  }
}
```

## Interpretation

- The GNN still beats the severity baseline on this test:
  `0.7586` vs `0.625 precision@24`.
- Calibration is still poor: ECE 0.3563 uncalibrated.
- Temperature does not change ranking or F1, only probabilities.
- Platt/isotonic collapse at the 0.5 threshold in this small test.
- Test is 24 positives / 16 negatives, dominated by header findings.

## Caveats

- The training set is only 46 reviewed records / 14 positives.
- 18 Juice Shop records are still pending human review.
- One external lab (WebGoat), one run.
- Transductive graph.
- No production score import.
- No claim of generalization.

## Artifacts

```text
backend/training/web_graph/evaluate_webgoat_external.py
backend/training/web_graph/web_external_webgoat.json
~/sentrix-gnn/src/web_external_webgoat_fixed.json
```

## Verdict

Allowed:

> “On a 40-record WebGoat external set with 24 human-reviewed positives, the
> pilot GNN achieved F1 0.7586 versus 0.625 precision@24 for a severity
> baseline. The training corpus is 46 human-reviewed records; calibration is
> still poor and the result is not production evidence.”

Not allowed:

> “The model generalizes to production web vulnerabilities.”
