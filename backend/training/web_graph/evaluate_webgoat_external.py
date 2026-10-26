"""External validation: train on Juice Shop batches 1+2, test on WebGoat batch 3."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from calibrate_web_gnn import (
    evaluate,
    fit_isotonic,
    fit_platt,
    fit_temperature,
    predict_isotonic,
)
from evaluate_web_gnn import train_model
from train_web_gnn import build_data, topk_metrics

SEVERITY_WEIGHT = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


def merge(a: dict, b: dict) -> dict:
    nodes = {node["id"]: node for node in a["nodes"] + b["nodes"]}
    edges = {(
        edge["source"], edge["type"], edge["target"]
    ): edge for edge in a["edges"] + b["edges"]}
    labels = dict(a["labels"])
    labels.update(b["labels"])
    return {"nodes": list(nodes.values()), "edges": list(edges.values()), "labels": labels}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("train_dataset", nargs="?", default="web_dataset_v2.json")
    parser.add_argument("test_dataset", nargs="?", default="web_dataset_batch3.json")
    parser.add_argument("--out", default="web_external_webgoat.json")
    parser.add_argument("--epochs", type=int, default=60)
    args = parser.parse_args()
    train_set = json.loads(Path(args.train_dataset).read_text())
    test_set = json.loads(Path(args.test_dataset).read_text())
    dataset = merge(train_set, test_set)
    data, _ = build_data(dataset)
    finding_ids = [node["id"] for node in dataset["nodes"] if node["type"] == "Finding"]
    train_mask = torch.tensor(
        [node_id.startswith(("finding:corpus-", "finding:b2-")) for node_id in finding_ids],
        dtype=torch.bool,
    )
    test_mask = torch.tensor(
        [node_id.startswith("finding:b3-") for node_id in finding_ids],
        dtype=torch.bool,
    )
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
    with torch.no_grad():
        logits = model(data)[:, 1]
    val_logits = logits[valid_mask]
    val_labels = data["Finding"].y[valid_mask]
    test_logits = logits[test_mask]
    test_labels = data["Finding"].y[test_mask].tolist()

    temperature = fit_temperature(val_logits, val_labels)
    platt_a, platt_b = fit_platt(val_logits, val_labels)
    isotonic_blocks = fit_isotonic(val_logits.tolist(), val_labels.tolist())

    test_set_nodes = [node for node in test_set["nodes"] if node["type"] == "Finding"]
    baseline = topk_metrics(
        [SEVERITY_WEIGHT.get(node["severity"], 0) for node in test_set_nodes],
        test_labels,
        k=sum(test_labels),
    )
    result = {
        "train": "Juice Shop batch 1+2",
        "test": "WebGoat batch 3",
        "trainSize": int(fit_mask.sum()),
        "validationSize": int(valid_mask.sum()),
        "testSize": int(test_mask.sum()),
        "testPositives": sum(test_labels),
        "severityBaseline": baseline,
        "uncalibrated": evaluate(torch.sigmoid(test_logits).tolist(), test_labels),
        "temperature": evaluate(torch.sigmoid(test_logits / temperature).tolist(), test_labels),
        "platt": evaluate(torch.sigmoid(platt_a * test_logits + platt_b).tolist(), test_labels),
        "isotonic": evaluate(predict_isotonic(isotonic_blocks, test_logits.tolist()), test_labels),
        "temperatureValue": round(temperature, 4),
        "plattA": round(platt_a, 4),
        "plattB": round(platt_b, 4),
    }
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
