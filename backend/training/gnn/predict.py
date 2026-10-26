"""Score one C function with the trained Devign AST-GAT baseline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch_geometric.data import Data

from graph_builder import build_ast_graph
from train_devign import GAT


def score(source: str, artifact: Path) -> dict:
    bundle = torch.load(artifact, map_location="cpu", weights_only=False)
    type_index = bundle["type_index"]
    graph = build_ast_graph(source, with_cfg=True)
    x = torch.tensor(
        [
            type_index.get(
                f"{node['type']}:{min(node.get('degree', 0), 10)}",
                type_index["<unk>"],
            )
            for node in graph.nodes
        ],
        dtype=torch.long,
    )
    edge_index = (
        torch.tensor(graph.edges, dtype=torch.long).t().contiguous()
        if graph.edges
        else torch.empty((2, 0), dtype=torch.long)
    )
    data = Data(x=x, edge_index=edge_index, batch=torch.zeros(len(graph.nodes), dtype=torch.long))
    model = GAT(len(type_index))
    model.load_state_dict(bundle["state_dict"])
    model.eval()
    with torch.no_grad():
        probability = torch.softmax(model(data), dim=1)[0, 1].item()
    return {
        "model": bundle["model"],
        "function": graph.function_name,
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "vulnerableProbability": round(probability, 4),
        "threshold": 0.5,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="path to a C file")
    parser.add_argument(
        "--artifact",
        default=str(Path.home() / "sentrix-gnn/artifacts/devign-gat/model.pt"),
    )
    args = parser.parse_args()
    print(json.dumps(score(Path(args.source).read_text(), Path(args.artifact)), indent=2))
