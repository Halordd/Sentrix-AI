"""Compare temperature, Platt and isotonic calibration on cross-batch validation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from torch import nn

from evaluate_web_gnn import (
    brier,
    ece,
    group_masks,
    train_model,
)
from train_web_gnn import build_data, metrics


def fit_temperature(validation_logits: torch.Tensor, labels: torch.Tensor) -> float:
    log_temperature = torch.zeros((), requires_grad=True)
    optimizer = torch.optim.LBFGS([log_temperature], lr=0.1, max_iter=80)
    criterion = nn.BCEWithLogitsLoss()

    def closure():
        optimizer.zero_grad()
        loss = criterion(validation_logits / torch.exp(log_temperature), labels.float())
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(torch.exp(log_temperature).detach().item())


def fit_platt(validation_logits: torch.Tensor, labels: torch.Tensor) -> tuple[float, float]:
    a = torch.ones((), requires_grad=True)
    b = torch.zeros((), requires_grad=True)
    optimizer = torch.optim.LBFGS([a, b], lr=0.1, max_iter=80)
    criterion = nn.BCEWithLogitsLoss()

    def closure():
        optimizer.zero_grad()
        loss = criterion(a * validation_logits + b, labels.float())
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(a.detach()), float(b.detach())


def fit_isotonic(scores: list[float], labels: list[int]) -> list[tuple[float, float]]:
    pairs = sorted(zip(scores, labels))
    # Pool adjacent violators.
    blocks: list[list[float]] = []
    for score, label in pairs:
        blocks.append([score, float(label), 1.0])
        while len(blocks) >= 2 and blocks[-2][1] / blocks[-2][2] > blocks[-1][1] / blocks[-1][2]:
            right = blocks.pop()
            left = blocks.pop()
            blocks.append([left[0], left[1] + right[1], left[2] + right[2]])
    return [(score, value / weight) for score, value, weight in blocks]


def predict_isotonic(blocks: list[tuple[float, float]], scores: list[float]) -> list[float]:
    if not blocks:
        return [0.5] * len(scores)
    result = []
    for score in scores:
        if score <= blocks[0][0]:
            result.append(blocks[0][1])
        elif score >= blocks[-1][0]:
            result.append(blocks[-1][1])
        else:
            for (left_x, left_y), (right_x, right_y) in zip(blocks, blocks[1:]):
                if left_x <= score <= right_x:
                    span = right_x - left_x
                    ratio = 0.0 if span == 0 else (score - left_x) / span
                    result.append(left_y + ratio * (right_y - left_y))
                    break
    return result


def evaluate(probabilities, labels):
    threshold = 0.5
    binary = [1 if prob >= threshold else 0 for prob in probabilities]
    tp = sum(1 for pred, label in zip(binary, labels) if pred == 1 and label == 1)
    fp = sum(1 for pred, label in zip(binary, labels) if pred == 1 and label == 0)
    fn = sum(1 for pred, label in zip(binary, labels) if pred == 0 and label == 1)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "ece": ece(probabilities, labels),
        "brier": brier(probabilities, labels),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", default="web_dataset_v2_reviewed.json")
    parser.add_argument("--out", default="web_calibration_compare.json")
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
        validation_logits = logits[valid_mask]
        validation_labels = data["Finding"].y[valid_mask]
        test_logits = logits[test_mask]
        test_labels = data["Finding"].y[test_mask].tolist()

        temperature = fit_temperature(validation_logits, validation_labels)
        platt_a, platt_b = fit_platt(validation_logits, validation_labels)
        isotonic_blocks = fit_isotonic(validation_logits.tolist(), validation_labels.tolist())

        base_probs = torch.sigmoid(test_logits).tolist()
        temperature_probs = torch.sigmoid(test_logits / temperature).tolist()
        platt_probs = torch.sigmoid(platt_a * test_logits + platt_b).tolist()
        isotonic_probs = predict_isotonic(isotonic_blocks, test_logits.tolist())

        results[f"train_{train_name}_test_{test_name}"] = {
            "validationSize": int(valid_mask.sum()),
            "temperatureValue": round(temperature, 4),
            "plattParams": {"a": round(platt_a, 4), "b": round(platt_b, 4)},
            "isotonicBlocks": len(isotonic_blocks),
            "uncalibrated": evaluate(base_probs, test_labels),
            "temperature": evaluate(temperature_probs, test_labels),
            "platt": evaluate(platt_probs, test_labels),
            "isotonic": evaluate(isotonic_probs, test_labels),
        }
    Path(args.out).write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
