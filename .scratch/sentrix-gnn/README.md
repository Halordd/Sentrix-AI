# SENTRIX GNN workspace

Goal: real GNN vulnerability triage with the Devign dataset.

| Ticket | Status |
|---|---|
| GNN-01 VM03 torch/PyG/tree-sitter | **done** |
| GNN-02 Clone ReVeal/Devign | **done** |
| GNN-03 Real dataset + hashes | **done — Devign HF mirror, MIT card** |
| GNN-04 AST graph builder | **done** |
| GNN-05 CFG/PDG edges | **partial — approximate CFG only** |
| GNN-06 GAT training | **done — weak measured baseline** |
| GNN-07 Model artifact + metrics | **done** |
| GNN-08 GNN inference service | **done — `/v1/score`** |
| GNN-09 Score import to candidate queue | **blocked — no finding→source mapping** |
| GNN-10 20 real findings L2/L3 | **blocked — white-box C corpus needed** |

## Latest measured result

Full train split:

```text
train=18676 valid=421 test=423
test precision=0.4713 recall=0.9899 f1=0.6386 accuracy=0.4728
threshold=0.41
```

Subset:

```text
train=2142 test f1=0.6429
threshold=0.39
```

The model is weak and predicts positive too often. It is not production quality.

Artifacts:

```text
~/sentrix-gnn/artifacts/devign-gat-full/model.pt
~/sentrix-gnn/artifacts/devign-gat-full/metrics.json
```

Service:

```text
GET  http://10.20.10.30:8002/health
POST http://10.20.10.30:8002/v1/score
```

## Blocked

- scanner + C finding→function mapping
- score import into automation queue
- 20 real lab findings L2/L3

See [`docs/phase2/29-gnn-improvement-run.md`](../../docs/phase2/29-gnn-improvement-run.md).
