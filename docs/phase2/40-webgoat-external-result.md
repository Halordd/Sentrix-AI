# SENTRIX — External validation on WebGoat

| Field | Value |
|---|---|
| Document ID | `SENTRIX-WEB-GNN-RUN-006` |
| Date | 2026-10-26 |
| Train | Juice Shop batches 1+2, 101 records / 40 positive |
| Test | WebGoat batch 3, 40 records / 24 positive |
| Model | Heterogeneous SAGE |
| Status | Pilot external validation |

## Result

```json
{
  "testSize": 40,
  "testPositives": 24,
  "severityBaseline": {
    "k": 24,
    "precisionAtK": 0.625,
    "recallAtK": 0.625,
    "hits": 15
  },
  "uncalibrated": {
    "precision": 1.0,
    "recall": 0.8333,
    "f1": 0.9091,
    "ece": 0.1771,
    "brier": 0.0983
  },
  "temperature": {
    "precision": 1.0,
    "recall": 0.8333,
    "f1": 0.9091,
    "ece": 0.31,
    "brier": 0.1827
  },
  "platt": {
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0
  },
  "isotonic": {
    "precision": 0.6316,
    "recall": 1.0,
    "f1": 0.7742,
    "ece": 0.2241
  }
}
```

## Interpretation

- On this WebGoat test set, the GNN achieved F1 0.9091 and beat the severity
  baseline (precision@24 0.625).
- Uncalibrated probabilities had the best ECE (0.1771) and Brier (0.0983).
- Temperature, Platt and isotonic all made calibration worse again.
- Platt collapsed (a=0.1299), so it is not usable.

## Critical caveats

- Test is 40 records / 24 positives, not production scale.
- The graph is transductive: WebGoat test nodes were present during graph
  construction, though their labels were not used in training.
- The test is dominated by header findings, which are similar to training
  header findings. This makes the task easier than “detect any web vuln”.
- One external lab, one run.
- No independent second external lab beyond WebGoat.
- Endpoint identity ablation previously hurt; the production candidate should
  likely drop endpoint one-hot features.
- Score import still blocked by the missing DB mapping.

## Artifacts

```text
backend/training/web_graph/evaluate_webgoat_external.py
backend/training/web_graph/web_external_webgoat.json
~/sentrix-gnn/src/web_external_webgoat.json
```

## Verdict

This is a **positive pilot external result**, not permission to import production
scores.

Allowed claim:

> “On a 40-record WebGoat external set with 24 human-reviewed positives, the
> pilot GNN achieved F1 0.9091 versus 0.625 precision@24 for a severity baseline.
> The test is small and dominated by header findings; calibration was not
> improved by post-hoc methods.”

Not allowed:

> “The model generalizes to web vulnerabilities in production.”
