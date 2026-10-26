"""Train a small heterogeneous web/API GNN on the 60-record lab corpus.

This is a pilot, not a generalization claim. The graph is transductive and the
corpus has only 20 positives.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from torch import nn
from torch_geometric.data import HeteroData
from torch_geometric.nn import HeteroConv, SAGEConv
from torch_geometric.transforms import ToUndirected

SEVERITY = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
SOURCES = ["DAST", "SAST", "MANUAL", "SCANNER", "DEMO"]


def one_hot(value, values):
    vector = [0.0] * len(values)
    if value in values:
        vector[values.index(value)] = 1.0
    return vector


def build_data(dataset: dict) -> tuple[HeteroData, dict]:
    nodes_by_type: dict[str, list[dict]] = {}
    for node in dataset["nodes"]:
        if node["type"] == "Verification":
            # Labels are derived from verification; using this node would leak.
            continue
        nodes_by_type.setdefault(node["type"], []).append(node)
    index = {
        node_type: {node["id"]: i for i, node in enumerate(nodes)}
        for node_type, nodes in nodes_by_type.items()
    }
    data = HeteroData()
    findings = nodes_by_type["Finding"]
    data["Finding"].x = torch.tensor(
        [
            one_hot(node["severity"], SEVERITY) + one_hot(node["source"], SOURCES)
            for node in findings
        ],
        dtype=torch.float,
    )
    endpoints = nodes_by_type.get("Endpoint", [])
    if endpoints:
        data["Endpoint"].x = torch.eye(len(endpoints))
    cwes = nodes_by_type.get("CWE", [])
    if cwes:
        data["CWE"].x = torch.eye(len(cwes))
    evidence = nodes_by_type.get("Evidence", [])
    if evidence:
        data["Evidence"].x = torch.tensor(
            [
                [
                    min(float(node.get("status") or 0) / 500.0, 1.0),
                    1.0 if "json" in str(node).lower() else 0.0,
                ]
                for node in evidence
            ],
            dtype=torch.float,
        )
    if nodes_by_type.get("Target"):
        data["Target"].x = torch.ones((len(nodes_by_type["Target"]), 1))

    edge_lists: dict[tuple[str, str, str], list[tuple[int, int]]] = {}
    prefix_to_type = {
        node["id"].split(":", 1)[0].lower(): node["type"] for node in dataset["nodes"]
    }
    for edge in dataset["edges"]:
        if edge["type"] == "VERIFIED_BY":
            continue
        source_prefix, source_id = edge["source"].split(":", 1)
        target_prefix, target_id = edge["target"].split(":", 1)
        source_type = prefix_to_type.get(source_prefix.lower())
        target_type = prefix_to_type.get(target_prefix.lower())
        if source_type not in index or target_type not in index:
            continue
        key = (source_type, edge["type"].lower(), target_type)
        edge_lists.setdefault(key, []).append(
            (index[source_type][edge["source"]], index[target_type][edge["target"]])
        )
    for key, edges in edge_lists.items():
        data[key].edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    data = ToUndirected()(data)
    labels = dataset["labels"]
    data["Finding"].y = torch.tensor(
        [int(labels[node["id"].removeprefix("finding:")]) for node in findings],
        dtype=torch.long,
    )
    return data, index


def split_indices(labels: list[int], seed: int = 42):
    rng = random.Random(seed)
    positives = [i for i, label in enumerate(labels) if label == 1]
    negatives = [i for i, label in enumerate(labels) if label == 0]
    rng.shuffle(positives)
    rng.shuffle(negatives)
    train = positives[:12] + negatives[:24]
    valid = positives[12:16] + negatives[24:32]
    test = positives[16:] + negatives[32:]
    for group in (train, valid, test):
        group.sort()
    return train, valid, test


def pr_auc(probs: list[float], labels: list[int]) -> float:
    pairs = sorted(zip(probs, labels), reverse=True)
    tp = fp = 0
    positives = sum(labels)
    points = [(0.0, 1.0)]
    for _, label in pairs:
        if label:
            tp += 1
        else:
            fp += 1
        points.append((fp / max(1, len(labels) - positives), tp / max(1, positives)))
    area = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        area += (x1 - x0) * (y0 + y1) / 2
    return area


def topk_metrics(scores: list[float], labels: list[int], k: int) -> dict:
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    hit = sum(labels[i] for i in order)
    positives = sum(labels)
    return {
        "k": k,
        "precisionAtK": round(hit / max(1, k), 4),
        "recallAtK": round(hit / max(1, positives), 4),
        "hits": hit,
        "positives": positives,
    }


def metrics(probs, labels, threshold=0.5):
    tp = sum(1 for p, y in zip(probs, labels) if p >= threshold and y == 1)
    fp = sum(1 for p, y in zip(probs, labels) if p >= threshold and y == 0)
    fn = sum(1 for p, y in zip(probs, labels) if p < threshold and y == 1)
    tn = sum(1 for p, y in zip(probs, labels) if p < threshold and y == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round((tp + tn) / max(1, len(labels)), 4),
        "prAuc": round(pr_auc(probs, labels), 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


class WebHGT(nn.Module):
    def __init__(self, data: HeteroData, hidden: int = 32) -> None:
        super().__init__()
        self.lin = nn.ModuleDict(
            {node_type: nn.Linear(data[node_type].x.shape[1], hidden) for node_type in data.node_types}
        )
        self.conv1 = HeteroConv(
            {edge_type: SAGEConv(hidden, hidden) for edge_type in data.edge_types},
            aggr="sum",
        )
        self.conv2 = HeteroConv(
            {edge_type: SAGEConv(hidden, hidden) for edge_type in data.edge_types},
            aggr="sum",
        )
        self.head = nn.Linear(hidden, 2)

    @staticmethod
    def _convs(conv, x, edge_index):
        out = conv(x, edge_index)
        return {node_type: out.get(node_type, x[node_type]) for node_type in x}

    def forward(self, data):
        x = {node_type: torch.relu(self.lin[node_type](data[node_type].x)) for node_type in data.node_types}
        edge_index = {
            edge_type: data[edge_type].edge_index for edge_type in data.edge_types
        }
        x = self._convs(self.conv1, x, edge_index)
        x = {key: torch.relu(value) for key, value in x.items()}
        x = self._convs(self.conv2, x, edge_index)
        return self.head(x["Finding"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", default="web_dataset_combined.json")
    parser.add_argument("--out", default="artifacts/web-hgt")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--hidden", type=int, default=32)
    args = parser.parse_args()
    dataset = json.loads(Path(args.dataset).read_text())
    data, _ = build_data(dataset)
    labels = data["Finding"].y.tolist()
    train, valid, test = split_indices(labels)
    train_mask = torch.zeros(len(labels), dtype=torch.bool)
    valid_mask = torch.zeros(len(labels), dtype=torch.bool)
    test_mask = torch.zeros(len(labels), dtype=torch.bool)
    train_mask[train] = True
    valid_mask[valid] = True
    test_mask[test] = True
    data["Finding"].train_mask = train_mask
    data["Finding"].valid_mask = valid_mask
    data["Finding"].test_mask = test_mask
    model = WebHGT(data, hidden=args.hidden)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    positive = sum(labels[i] for i in train)
    negative = len(train) - positive
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor([len(train) / (2 * max(1, negative)), len(train) / (2 * max(1, positive))])
    )
    best_state = None
    best_f1 = -1
    for epoch in range(1, args.epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(data)
        loss = criterion(logits[train_mask], data["Finding"].y[train_mask])
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0 or epoch == args.epochs:
            model.eval()
            with torch.no_grad():
                probs = torch.softmax(model(data), dim=1)[:, 1].tolist()
            valid_metrics = metrics([probs[i] for i in valid], [labels[i] for i in valid])
            if valid_metrics["f1"] > best_f1:
                best_f1 = valid_metrics["f1"]
                best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            print({"epoch": epoch, "loss": round(float(loss.detach()), 4), "valid": valid_metrics})
    if best_state:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        probs = torch.softmax(model(data), dim=1)[:, 1].tolist()
    test_metrics = metrics([probs[i] for i in test], [labels[i] for i in test])
    finding_nodes = [node for node in dataset["nodes"] if node["type"] == "Finding"]
    severity_weight = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    baseline_scores = [
        severity_weight.get(finding_nodes[i]["severity"], 0) for i in test
    ]
    baseline_metrics = topk_metrics(
        baseline_scores,
        [labels[i] for i in test],
        k=sum(labels[i] for i in test),
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "hidden": args.hidden}, out / "model.pt")
    result = {
        "dataset": "sentrix-web-lab-corpus",
        "model": "HeteroConv-SAGE",
        "nodes": data.num_nodes,
        "edges": data.num_edges,
        "train": len(train), "valid": len(valid), "test": len(test),
        "positives": sum(labels),
        "seed": 42,
        "test": test_metrics,
        "severity_baseline_on_same_test": baseline_metrics,
    }
    (out / "metrics.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
