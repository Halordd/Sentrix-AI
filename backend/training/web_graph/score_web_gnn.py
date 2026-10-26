"""Train on the Juice Shop corpus and save a candidate score per finding."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from evaluate_webgoat_external import merge
from evaluate_web_gnn import train_model
from train_web_gnn import build_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("train_dataset", nargs="?", default="web_dataset_v2.json")
    parser.add_argument("test_dataset", nargs="?", default="web_dataset_batch3.json")
    parser.add_argument("--out", default="web_scores.json")
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
        probs = torch.sigmoid(model(data)[:, 1]).tolist()
    labels = dataset["labels"]
    scores = {}
    for node_id, score in zip(finding_ids, probs):
        source_id = node_id.removeprefix("finding:")
        scores[source_id] = {
            "score": round(float(score), 6),
            "label": labels.get(source_id),
            "split": "train" if source_id.startswith(("corpus-", "b2-")) else "webgoat",
        }
    Path(args.out).write_text(json.dumps(scores, indent=2))
    print(json.dumps({"output": args.out, "records": len(scores), "min": min(s["score"] for s in scores.values()), "max": max(s["score"] for s in scores.values())}, indent=2))


if __name__ == "__main__":
    main()
