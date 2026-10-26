"""5-seed and ablation runner for the web/API GNN pilot."""
from __future__ import annotations

import argparse
import copy
import json
import statistics
from pathlib import Path

import torch
from torch import nn

from train_web_gnn import WebHGT, build_data, metrics, split_indices, topk_metrics

SEVERITY_WEIGHT = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
ABLATIONS = {
    "full": (set(), set()),
    "no_graph": (set(), set()),
    "no_evidence": ({"Evidence"}, {"HAS_EVIDENCE"}),
    "no_endpoint": ({"Endpoint"}, {"EXPOSES", "HAS_FINDING"}),
    "no_cwe": ({"CWE"}, {"HAS_CWE"}),
}


class FeatureMLP(nn.Module):
    def __init__(self, input_dim: int, hidden: int = 32) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 2),
        )

    def forward(self, data):
        return self.net(data["Finding"].x)


def subset(dataset: dict, drop_nodes: set[str], drop_edges: set[str]) -> dict:
    data = copy.deepcopy(dataset)
    removed = {
        node["id"] for node in data["nodes"] if node["type"] in drop_nodes
    }
    data["nodes"] = [node for node in data["nodes"] if node["id"] not in removed]
    data["edges"] = [
        edge
        for edge in data["edges"]
        if edge["type"] not in drop_edges
        and edge["source"] not in removed
        and edge["target"] not in removed
    ]
    return data


def run_one(dataset: dict, seed: int, ablation: str, epochs: int = 60) -> dict:
    drop_nodes, drop_edges = ABLATIONS[ablation]
    filtered = subset(dataset, drop_nodes, drop_edges)
    torch.manual_seed(seed)
    data, _ = build_data(filtered)
    labels = data["Finding"].y.tolist()
    train, valid, test = split_indices(labels, seed)
    for split, mask_name in ((train, "train_mask"), (valid, "valid_mask"), (test, "test_mask")):
        mask = torch.zeros(len(labels), dtype=torch.bool)
        mask[split] = True
        setattr(data["Finding"], mask_name, mask)
    if ablation == "no_graph":
        model = FeatureMLP(data["Finding"].x.shape[1])
    else:
        model = WebHGT(data, hidden=32)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    positive = sum(labels[i] for i in train)
    negative = len(train) - positive
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor([len(train) / (2 * max(1, negative)), len(train) / (2 * max(1, positive))])
    )
    best_state = None
    best_f1 = -1.0
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(data)
        loss = criterion(logits[data["Finding"].train_mask], data["Finding"].y[data["Finding"].train_mask])
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0 or epoch == epochs:
            model.eval()
            with torch.no_grad():
                probs = torch.softmax(model(data), dim=1)[:, 1].tolist()
            valid_f1 = metrics(
                [probs[i] for i in valid], [labels[i] for i in valid]
            )["f1"]
            if valid_f1 > best_f1:
                best_f1 = valid_f1
                best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
    if best_state:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        probs = torch.softmax(model(data), dim=1)[:, 1].tolist()
    test_metrics = metrics([probs[i] for i in test], [labels[i] for i in test])
    finding_nodes = [node for node in filtered["nodes"] if node["type"] == "Finding"]
    baseline = topk_metrics(
        [SEVERITY_WEIGHT.get(finding_nodes[i]["severity"], 0) for i in test],
        [labels[i] for i in test],
        k=sum(labels[i] for i in test),
    )
    return {
        "seed": seed,
        "ablation": ablation,
        "validBestF1": round(best_f1, 4),
        "test": test_metrics,
        "severityBaseline": baseline,
    }


def aggregate(rows: list[dict]) -> dict:
    test_f1 = [row["test"]["f1"] for row in rows]
    test_precision = [row["test"]["precision"] for row in rows]
    test_recall = [row["test"]["recall"] for row in rows]
    test_pr_auc = [row["test"]["prAuc"] for row in rows]
    baseline = [row["severityBaseline"]["precisionAtK"] for row in rows]
    return {
        "runs": len(rows),
        "test_f1_mean": round(statistics.mean(test_f1), 4),
        "test_f1_std": round(statistics.pstdev(test_f1), 4),
        "test_precision_mean": round(statistics.mean(test_precision), 4),
        "test_recall_mean": round(statistics.mean(test_recall), 4),
        "test_prAuc_mean": round(statistics.mean(test_pr_auc), 4),
        "severity_precisionAtK_mean": round(statistics.mean(baseline), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", default="web_dataset_combined.json")
    parser.add_argument("--out", default="web_experiments.json")
    parser.add_argument("--epochs", type=int, default=60)
    args = parser.parse_args()
    dataset = json.loads(Path(args.dataset).read_text())
    results = {}
    for ablation in ABLATIONS:
        rows = [run_one(dataset, seed, ablation, args.epochs) for seed in (1, 2, 3, 4, 5)]
        results[ablation] = {"runs": rows, "aggregate": aggregate(rows)}
        print(ablation, json.dumps(results[ablation]["aggregate"]))
    Path(args.out).write_text(json.dumps(results, indent=2))
    print(json.dumps({"output": args.out, "ablations": list(results)}, indent=2))


if __name__ == "__main__":
    main()
