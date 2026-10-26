"""External batch validation + calibration for the SENTRIX web GNN."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch import nn

from train_web_gnn import WebHGT, build_data, metrics, topk_metrics

SEVERITY_WEIGHT = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


def group_masks(finding_ids: list[str], group: str) -> torch.Tensor:
    prefix = "finding:corpus-" if group == "batch1" else "finding:b2-"
    return torch.tensor([node_id.startswith(prefix) for node_id in finding_ids], dtype=torch.bool)


def train_model(data, train_mask, valid_mask=None, epochs: int = 60):
    labels = data["Finding"].y
    model = WebHGT(data, hidden=32)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    positives = int(labels[train_mask].sum())
    negatives = int(train_mask.sum()) - positives
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor(
            [len(labels[train_mask]) / (2 * max(1, negatives)), len(labels[train_mask]) / (2 * max(1, positives))]
        )
    )
    best_state = None
    best_f1 = -1.0
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()
        loss = criterion(model(data)[train_mask], labels[train_mask])
        loss.backward()
        optimizer.step()
        if valid_mask is not None and (epoch % 10 == 0 or epoch == epochs):
            model.eval()
            with torch.no_grad():
                probs = torch.softmax(model(data), dim=1)[:, 1]
            f1 = metrics(probs[valid_mask].tolist(), labels[valid_mask].tolist())["f1"]
            if f1 > best_f1:
                best_f1 = f1
                best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
    if best_state:
        model.load_state_dict(best_state)
    return model


def logits_for(model, data):
    model.eval()
    with torch.no_grad():
        return model(data)


def ece(probs, labels, bins=10):
    total = len(probs)
    value = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        members = [i for i, prob in enumerate(probs) if low <= prob < high or (index == bins - 1 and prob == 1.0)]
        if not members:
            continue
        avg_conf = sum(probs[i] for i in members) / len(members)
        accuracy = sum(labels[i] for i in members) / len(members)
        value += len(members) / total * abs(avg_conf - accuracy)
    return round(value, 4)


def brier(probs, labels):
    return round(sum((prob - label) ** 2 for prob, label in zip(probs, labels)) / max(1, len(labels)), 4)


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    log_temperature = torch.zeros((), requires_grad=True)
    optimizer = torch.optim.LBFGS([log_temperature], lr=0.1, max_iter=50)
    criterion = nn.CrossEntropyLoss()

    def closure():
        optimizer.zero_grad()
        loss = criterion(logits / torch.exp(log_temperature), labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(torch.exp(log_temperature).detach().item())


def evaluate(model, data, mask, temperature=1.0):
    logits = logits_for(model, data)
    probabilities = torch.softmax(logits / temperature, dim=1)[:, 1]
    y = data["Finding"].y
    mask_list = mask.tolist()
    probs = probabilities[mask].tolist()
    labels = y[mask].tolist()
    return {
        "metrics": metrics(probs, labels),
        "calibration": {
            "ece": ece(probs, labels),
            "brier": brier(probs, labels),
            "temperature": round(temperature, 4),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", default="web_dataset_v2.json")
    parser.add_argument("--out", default="web_external_calibration.json")
    parser.add_argument("--epochs", type=int, default=60)
    args = parser.parse_args()
    dataset = json.loads(Path(args.dataset).read_text())
    data, _ = build_data(dataset)
    finding_ids = [node["id"] for node in dataset["nodes"] if node["type"] == "Finding"]
    batch1 = group_masks(finding_ids, "batch1")
    batch2 = group_masks(finding_ids, "batch2")
    results = {}

    for train_name, test_name, train_mask, test_mask in (
        ("batch1", "batch2", batch1, batch2),
        ("batch2", "batch1", batch2, batch1),
    ):
        # Split training group into fit/validation by index, stratified by label.
        indices = train_mask.nonzero(as_tuple=False).flatten().tolist()
        positives = [i for i in indices if int(data["Finding"].y[i]) == 1]
        negatives = [i for i in indices if int(data["Finding"].y[i]) == 0]
        fit_mask = torch.zeros_like(train_mask)
        valid_mask = torch.zeros_like(train_mask)
        for group in (positives, negatives):
            cut = max(1, int(len(group) * 0.8))
            for i in group[:cut]:
                fit_mask[i] = True
            for i in group[cut:]:
                valid_mask[i] = True
        model = train_model(data, fit_mask, valid_mask, args.epochs)
        # Calibrate on the held-out validation part of the training batch.
        with torch.no_grad():
            logits = model(data)
        temperature = fit_temperature(logits[valid_mask], data["Finding"].y[valid_mask])
        results[f"train_{train_name}_test_{test_name}"] = evaluate(model, data, test_mask, temperature)
        results[f"train_{train_name}_test_{test_name}"]["temperatureFitOn"] = "training-batch holdout"
    Path(args.out).write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
