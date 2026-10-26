# SENTRIX — first real Devign GAT run

| Field | Value |
|---|---|
| Document ID | `SENTRIX-GNN-RUN-001` |
| Date | 2026-10-26 |
| Status | Measured baseline, not production |
| Dataset | `AISE-TUDelft/ML4SE23_G6_Devign` |
| Dataset card license | MIT |
| Graph | AST only |
| Model | GAT, seed 42 |

## Dataset

Hugging Face dataset:
[`AISE-TUDelft/ML4SE23_G6_Devign`](https://huggingface.co/datasets/AISE-TUDelft/ML4SE23_G6_Devign)

Files downloaded to `~/sentrix-gnn/data/devign/`:

| File | SHA-256 |
|---|---|
| `train_devign.json` | `48a13d9e24ce8b17c54d9cc8e8eb5c39d013c92550cef00845916a4a6e20dfc1` |
| `valid_devign.json` | `9ac2a271915f5fdd0fce2971c22f6645d60db5ebfd07df01a405d6a0e5fa3a40` |
| `test_devign.json` | `204bbca11baa37e49081b139d33143ffcc57b7f2019d39c94a9ae5e76ef17b0b` |

The three files contain real Devign-style function records:

```json
{"target": 0, "idx": 0, "func": "static av_cold int vdadec_init(...) { ... }"}
```

The dataset card is MIT. The original paper/Devign data licence is not
independently re-verified here; this mirror is recorded as the source.

## Run

Environment on VM03:

```text
~/sentrix-gnn/venv
torch 2.14.1+cpu
torch-geometric 2.8.1
tree-sitter 0.26.0
tree-sitter-c 0.24.2
```

Command:

```bash
cd ~/sentrix-gnn/src
../venv/bin/python train_devign.py \
  --train-limit 1500 \
  --eval-limit 300 \
  --epochs 3
```

Dataset used by this run:

```text
train=1279 graphs
valid=244 graphs
test=245 graphs
node types=95
```

## Measured result

```json
{
  "test": {
    "precision": 0.4746,
    "recall": 0.9825,
    "f1": 0.64,
    "accuracy": 0.4857,
    "tp": 112,
    "fp": 124,
    "fn": 2,
    "tn": 7
  }
}
```

This is a **real measured baseline**, not a good production model. It predicts
the positive class too aggressively and has low specificity on this subset.

Artifacts:

```text
~/sentrix-gnn/artifacts/devign-gat/model.pt
~/sentrix-gnn/artifacts/devign-gat/metrics.json
```

## What this does and does not prove

Proves:

- real dataset download works;
- real function graph construction works;
- GAT training runs on CPU;
- metrics are measured with a fixed seed.

Does not prove:

- production vulnerability detection quality;
- black-box pentest coverage;
- cross-dataset generalization;
- CFG/PDG benefit;
- integration with SENTRIX findings.

## Critical limitation: domain mismatch

The model is a **C/C++ function-level code vulnerability classifier**. SENTRIX
findings are web/API authorization findings without C function source. A score
from this model cannot be assigned to those findings without a real source
mapping.

Therefore GNN scores are **not** imported into the candidate queue yet. Doing so
would be fabricated context.

## Next steps

1. Improve baseline: class weighting, early stopping, threshold calibration,
   full train split, CFG edges.
2. Add a source-ingestion path: finding → file/function mapping.
3. Validate the mapping with real white-box C code, not the web lab.
4. Add `GnnInferencePort`/HTTP service.
5. Only then import scores into `automation_candidate`.

## Status

```text
Real dataset: yes
Real AST graphs: yes
Real GAT training: yes
Measured metrics: yes (weak)
GNN → SENTRIX candidate queue: not yet
20 real findings L2/L3: not yet
```
