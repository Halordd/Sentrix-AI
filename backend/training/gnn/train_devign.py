"""Real Devign AST-GNN baseline.

Dataset: AISE-TUDelft/ML4SE23_G6_Devign on Hugging Face, MIT-licensed card.
The dataset is real Devign function-level data (target 0/1, func C source).

This trains on AST graphs only; CFG/PDG are out of scope for this run.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path

import torch
from torch import nn
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader
from torch_geometric.nn import GATConv, global_mean_pool

from graph_builder import build_ast_graph


def load_examples(path: Path, limit: int) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    random.Random(42).shuffle(rows)
    return rows if limit <= 0 else rows[:limit]


def to_data(row: dict, type_index: dict[str, int]) -> Data | None:
    try:
        graph = build_ast_graph(row["func"], with_cfg=True)
    except Exception:
        return None
    if not graph.nodes:
        return None
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
    if graph.edges:
        edge_index = torch.tensor(graph.edges, dtype=torch.long).t().contiguous()
    else:
        edge_index = torch.empty((2, 0), dtype=torch.long)
    return Data(x=x, edge_index=edge_index, y=torch.tensor([int(row["target"])], dtype=torch.long))


class GAT(nn.Module):
    def __init__(self, num_types: int, hidden: int = 64) -> None:
        super().__init__()
        self.embed = nn.Embedding(num_types, hidden)
        self.conv1 = GATConv(hidden, hidden, heads=2, dropout=0.2)
        self.conv2 = GATConv(hidden * 2, hidden, heads=1, dropout=0.2)
        self.head = nn.Linear(hidden, 2)

    def forward(self, data):
        x = self.embed(data.x)
        x = torch.relu(self.conv1(x, data.edge_index))
        x = torch.relu(self.conv2(x, data.edge_index))
        return self.head(global_mean_pool(x, data.batch))


def probabilities(model, loader) -> tuple[list[float], list[int]]:
    model.eval()
    probs: list[float] = []
    labels: list[int] = []
    with torch.no_grad():
        for batch in loader:
            probs.extend(torch.softmax(model(batch), dim=1)[:, 1].tolist())
            labels.extend(batch.y.view(-1).tolist())
    return probs, labels


def metrics_at(probs: list[float], labels: list[int], threshold: float = 0.5) -> dict:
    tp = fp = fn = tn = 0
    for probability, label in zip(probs, labels):
        pred = 1 if probability >= threshold else 0
        if pred == 1 and label == 1:
            tp += 1
        elif pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 1:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / max(1, tp + tn + fp + fn)
    return {
        "threshold": round(threshold, 3),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def metrics(model, loader, threshold: float = 0.5) -> dict:
    probs, labels = probabilities(model, loader)
    return metrics_at(probs, labels, threshold)


def calibrate(model, loader) -> tuple[float, dict]:
    probs, labels = probabilities(model, loader)
    best_threshold, best = 0.5, metrics_at(probs, labels, 0.5)
    for step in range(10, 91):
        threshold = step / 100
        candidate = metrics_at(probs, labels, threshold)
        if candidate["f1"] > best["f1"]:
            best_threshold, best = threshold, candidate
    return best_threshold, best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(Path.home() / "sentrix-gnn/data/devign"))
    parser.add_argument("--train-limit", type=int, default=0)
    parser.add_argument("--eval-limit", type=int, default=500)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--out", default=str(Path.home() / "sentrix-gnn/artifacts/devign-gat"))
    args = parser.parse_args()
    random.seed(42)
    torch.manual_seed(42)

    root = Path(args.data)
    train_rows = load_examples(root / "train_devign.json", args.train_limit)
    valid_rows = load_examples(root / "valid_devign.json", args.eval_limit)
    test_rows = load_examples(root / "test_devign.json", args.eval_limit)

    type_index = {"<unk>": 0}
    for row in train_rows:
        try:
            graph = build_ast_graph(row["func"], with_cfg=True)
        except Exception:
            continue
        for node in graph.nodes:
            key = f"{node['type']}:{min(node.get('degree', 0), 10)}"
            if key not in type_index:
                type_index[key] = len(type_index)

    def build(rows):
        data = []
        for row in rows:
            item = to_data(row, type_index)
            if item is not None:
                data.append(item)
        return data

    train = build(train_rows)
    valid = build(valid_rows)
    test = build(test_rows)
    print({"train": len(train), "valid": len(valid), "test": len(test), "types": len(type_index)})

    model = GAT(len(type_index), hidden=args.hidden)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=5e-4)
    labels = [int(item.y.item()) for item in train]
    positive = sum(labels)
    negative = len(labels) - positive
    weights = torch.tensor(
        [len(labels) / (2 * max(1, negative)), len(labels) / (2 * max(1, positive))]
    )
    criterion = nn.CrossEntropyLoss(weight=weights)
    train_loader = DataLoader(train, batch_size=32, shuffle=True)
    valid_loader = DataLoader(valid, batch_size=64)
    test_loader = DataLoader(test, batch_size=64)

    best = {"f1": -1.0}
    best_state = copy.deepcopy(model.state_dict())
    best_threshold = 0.5
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            loss = criterion(model(batch), batch.y.view(-1))
            loss.backward()
            optimizer.step()
            total += float(loss.detach())
        threshold, valid_metrics = calibrate(model, valid_loader)
        print(
            {
                "epoch": epoch,
                "loss": round(total / max(1, len(train_loader)), 4),
                "valid": valid_metrics,
            }
        )
        if valid_metrics["f1"] > best["f1"]:
            best = {"f1": valid_metrics["f1"], **valid_metrics}
            best_state = copy.deepcopy(model.state_dict())
            best_threshold = threshold

    model.load_state_dict(best_state)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "type_index": type_index,
            "model": "GAT-AST-CFG-devign",
            "threshold": best_threshold,
            "hidden": args.hidden,
            "train_limit": args.train_limit,
            "eval_limit": args.eval_limit,
        },
        out / "model.pt",
    )
    result = {
        "dataset": "AISE-TUDelft/ML4SE23_G6_Devign",
        "license": "MIT",
        "dataset_hashes": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("train_devign.json", "valid_devign.json", "test_devign.json")
        },
        "graph": "AST + approximate CFG",
        "model": "GAT",
        "seed": 42,
        "train": len(train),
        "valid": len(valid),
        "test": len(test),
        "best_valid": best,
        "threshold": best_threshold,
        "test": metrics(model, test_loader, best_threshold),
    }
    (out / "metrics.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
