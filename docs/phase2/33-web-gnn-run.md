# SENTRIX — Web/API GNN pilot result

| Field | Value |
|---|---|
| Document ID | `SENTRIX-WEB-GNN-RUN-001` |
| Date | 2026-10-26 |
| Dataset | 60 local web/API records |
| Positives | 20 human-reviewed |
| Negatives | 40 |
| Model | Heterogeneous SAGE (HeteroConv) |
| Graph | 179 nodes, 480 directed edges |
| Status | Pilot only; not production; not integrated |

## Dataset split

```text
train=36
valid=12
test=12
test positives=4
test negatives=8
```

Split is stratified by label, seed 42.

## Leakage fix

The first run produced F1 1.0. That was leakage: the `Verification` node exists
only for positive labels, so the model could read the label from graph structure.

Fix:

- removed `Verification` nodes;
- removed `VERIFIED_BY` edges;
- labels are used only in the loss/evaluation, never as input features.

The reported result below is after this fix.

## Result

```json
{
  "test": {
    "precision": 1.0,
    "recall": 0.75,
    "f1": 0.8571,
    "accuracy": 0.9167,
    "prAuc": 0.9062,
    "tp": 3,
    "fp": 0,
    "fn": 1,
    "tn": 8
  },
  "severity_baseline_on_same_test": {
    "k": 4,
    "precisionAtK": 0.25,
    "recallAtK": 0.25,
    "hits": 1,
    "positives": 4
  }
}
```

The GNN beat the severity heuristic on this tiny test set, but the test set has
only 4 positives. Treat this as a **pilot signal**, not evidence of
generalization.

## Artifacts

```text
~/sentrix-gnn/artifacts/web-hgt/model.pt
~/sentrix-gnn/artifacts/web-hgt/metrics.json
backend/training/web_graph/web_metrics.json
```

## Honest limitations

- 20 positives is very small.
- One seed, one split; no confidence interval.
- Test has 4 positives, so one error changes F1 heavily.
- Transductive graph; new records would need graph updates.
- Features are simple (severity, source, endpoint identity, evidence metadata).
- The model was selected on validation F1, then evaluated on test; still small.
- No external validation against another lab.
- No production inference integration yet.

## What this justifies in the thesis

Allowed:

> “On a 60-record local pilot corpus with 20 human-reviewed positives, a
> heterogeneous graph SAGE model achieved test F1 0.8571 versus 0.25
> precision@4 for a severity baseline. The test set is small, so this is a
> pilot result, not a generalization claim.”

Not allowed:

> “The GNN detects web vulnerabilities in production.”

## Next steps

1. Add a second independent lab/engagement.
2. Expand to 100+ records with 40+ positives.
3. Run 5 seeds and report mean/std.
4. Add ablations: no graph, no endpoint, no evidence.
5. Calibrate probabilities.
6. Only then consider importing scores into the candidate queue.
