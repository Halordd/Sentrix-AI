# GNN scaffold

`graph_builder.py` builds an AST graph from C source using tree-sitter.

```bash
~/sentrix-gnn/venv/bin/python - <<'PY'
from graph_builder import build_ast_graph
g = build_ast_graph("int f(int x){ if(x) return 1; return 0; }")
print(len(g.nodes), len(g.edges))
PY
```

Current status: AST only. CFG/PDG, dataset loader and GAT/GIN training are
blocked until a labelled ReVeal/Devign archive is available with a recorded
licence and SHA-256. See
[`docs/phase2/27-gnn-implementation-status.md`](../../docs/phase2/27-gnn-implementation-status.md).
