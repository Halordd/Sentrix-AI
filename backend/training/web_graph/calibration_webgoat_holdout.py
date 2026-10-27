"""Calibration on a held-out WebGoat half, evaluated on the other half."""
from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

import torch

from calibrate_web_gnn import evaluate, fit_isotonic, fit_platt, fit_temperature, predict_isotonic
from evaluate_web_gnn import train_model
from evaluate_webgoat_external import merge
from train_web_gnn import build_data

METHODS = ("uncalibrated", "temperature", "platt", "isotonic")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("train_dataset", nargs="?", default="web_dataset_v2_reviewed.json")
    parser.add_argument("test_dataset", nargs="?", default="web_dataset_batch3.json")
    parser.add_argument("--out", default="web_calibration_webgoat_holdout.json")
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
    b3_indices = [
        i for i, node_id in enumerate(finding_ids) if node_id.startswith("finding:b3-")
    ]
    b3_labels = [int(data["Finding"].y[i]) for i in b3_indices]
    positive_indices = [i for i, label in zip(b3_indices, b3_labels) if label == 1]
    negative_indices = [i for i, label in zip(b3_indices, b3_labels) if label == 0]
    results = {method: [] for method in METHODS}
    for seed in range(1, 6):
        rng = random.Random(seed)
        rng.shuffle(positive_indices)
        rng.shuffle(negative_indices)
        calibration = positive_indices[:12] + negative_indices[:8]
        test = positive_indices[12:] + negative_indices[8:]
        calibration_logits = logits[calibration]
        calibration_labels = torch.tensor([int(data["Finding"].y[i]) for i in calibration])
        test_logits = logits[test]
        test_labels = [int(data["Finding"].y[i]) for i in test]
        temperature = fit_temperature(calibration_logits, calibration_labels)
        a, b = fit_platt(calibration_logits, calibration_labels)
        blocks = fit_isotonic(calibration_logits.tolist(), calibration_labels.tolist())
        predictions = {
            "uncalibrated": torch.sigmoid(test_logits).tolist(),
            "temperature": torch.sigmoid(test_logits / temperature).tolist(),
            "platt": torch.sigmoid(a * test_logits + b).tolist(),
            "isotonic": predict_isotonic(blocks, test_logits.tolist()),
        }
        for method, probabilities in predictions.items():
            results[method].append(evaluate(probabilities, test_labels))
    summary = {}
    for method, rows in results.items():
        summary[method] = {
            "runs": len(rows),
            "f1Mean": round(statistics.mean(row["f1"] for row in rows), 4),
            "f1Std": round(statistics.pstdev(row["f1"] for row in rows), 4),
            "eceMean": round(statistics.mean(row["ece"] for row in rows), 4),
            "eceStd": round(statistics.pstdev(row["ece"] for row in rows), 4),
            "brierMean": round(statistics.mean(row["brier"] for row in rows), 4),
        }
    Path(args.out).write_text(json.dumps({"summary": summary, "runs": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
