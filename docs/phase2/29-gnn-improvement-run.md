# SENTRIX — GNN improvement run

| Field | Value |
|---|---|
| Document ID | `SENTRIX-GNN-RUN-002` |
| Date | 2026-10-26 |
| Status | Measured baseline; weak; not integrated |
| Dataset | `AISE-TUDelft/ML4SE23_G6_Devign` |
| Dataset card license | MIT |
| Model | GAT, AST + approximate CFG, seed 42 |

## What changed

- class weighting computed from train label balance;
- threshold calibration on validation (0.10–0.90);
- full train split run;
- approximate CFG edges added between statements and control bodies;
- degree-aware node type features;
- GNN HTTP inference service (`/v1/score`).

## Full train run

```text
train=18676
valid=421
test=423
node types=343
epochs=3
```

Result:

```json
{
  "threshold": 0.41,
  "precision": 0.4713,
  "recall": 0.9899,
  "f1": 0.6386,
  "accuracy": 0.4728,
  "tp": 197,
  "fp": 221,
  "fn": 2,
  "tn": 3
}
```

Subset improved run:

```json
{
  "train": 2142,
  "threshold": 0.39,
  "precision": 0.4796,
  "recall": 0.9745,
  "f1": 0.6429,
  "accuracy": 0.4895
}
```

## Honest judgment

The improvements did **not** materially improve the baseline. The model still
predicts the positive class too aggressively. AST + approximate CFG + node-type
features are not enough for this dataset. Do not use this model as a claim of
good vulnerability detection.

Artifacts:

```text
~/sentrix-gnn/artifacts/devign-gat-full/model.pt
~/sentrix-gnn/artifacts/devign-gat-full/metrics.json
```

## GNN inference service

Source: `backend/training/gnn/service.py`

```text
GET  /health
POST /v1/score  {"source":"int f(...) {...}"}
```

Tested on VM03:

```json
{
  "model": "GAT-AST-CFG-devign",
  "function": "add(int a, int b)",
  "nodes": 21,
  "edges": 21,
  "vulnerableProbability": 0.4249
}
```

The service is **source-only**; it does not contact a target.

## Still blocked

### Scanner + finding → function mapping

SENTRIX findings are web/API authorization findings. The GNN is a C/C++
function classifier. There is no valid source mapping. Adding a scanner on the
web lab would still not produce C functions.

### Score import into candidate queue

The candidate queue accepts `score`, but writing a GNN score for a web finding
would be fabricated context. Not done.

### 20 real findings L2/L3

Not done. Requires a white-box C corpus, scanner findings and function mapping.

## Decision point

Choose:

1. **White-box C path**: add a C target + scanner + finding→function mapping,
   then use this GNN.
2. **Black-box network path**: build a network/flow graph dataset and a
   different GNN. The current C model does not apply.

Do not mix the two and call it the same experiment.
