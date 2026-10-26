# SENTRIX GNN implementation status

| Field | Value |
|---|---|
| Document ID | `SENTRIX-GNN-STATUS-001` |
| Date | 2026-10-26 |
| Status | Environment ready; dataset blocked; no trained model yet |

## Completed

### VM03 environment

- Python 3.12.3
- CPU `torch 2.14.1+cpu`
- `torch-geometric 2.8.1`
- `tree-sitter 0.26.0`
- `tree-sitter-c 0.24.2`
- venv: `~/sentrix-gnn/venv`

### Repositories

- `~/sentrix-gnn/ReVeal` at `ca31b78`
- `~/sentrix-gnn/Devign` at `be2f831`

### Graph builder smoke test

`backend/training/gnn/graph_builder.py` parses a C function with tree-sitter:

```text
function=add(int a, int b)
nodes=21
edges=20
```

This is an AST graph only. CFG/PDG edges are not implemented yet.

## Blocked: real dataset

### ReVeal

`data/get_data.sh` points to a Google Drive file ID. Download returned an HTML
**404 Not Found** page, not a zip. The repository is MIT-licensed, but the data
file is not retrievable from that link; dataset licence cannot be recorded.

### Devign

Repository clone contains code only. No dataset archive or licence file is
included. The original dataset URL is not documented in the cloned README.

Therefore:

- dataset hash: **not recorded**
- dataset licence: **not recorded**
- train/validation/test split: **not created**
- GNN metrics: **not produced**

## Not implemented

- ReVeal/Devign loader
- CFG/PDG graph construction
- GAT/GIN training
- model artifact
- score import into `automation_candidate`
- L2 vs L3 on real findings

## Required to continue

Provide one of:

1. A locally downloaded ReVeal/Devign archive with its licence and source URL.
2. An approved alternative labelled dataset with a clear licence.
3. Permission to use a public mirror and a specific licence to record.

Then the next steps are deterministic:

1. Verify archive SHA-256.
2. Record licence and split.
3. Build AST+CFG graphs.
4. Train GAT/GIN with a fixed seed.
5. Export model card + metrics.
6. Generate candidate scores.
7. Run L2 vs L3 on 20 real lab findings.
