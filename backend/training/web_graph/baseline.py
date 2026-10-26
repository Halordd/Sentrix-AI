"""Severity heuristic baseline for the 20-record web corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SCORE = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", default="web_dataset.json")
    args = parser.parse_args()
    dataset = json.loads(Path(args.dataset).read_text())
    findings = {node["id"].removeprefix("finding:"): node for node in dataset["nodes"] if node["type"] == "Finding"}
    records = sorted(
        findings.values(),
        key=lambda node: (SCORE.get(node["severity"], 0), node["title"]),
        reverse=True,
    )
    labels = {key: value for key, value in dataset["labels"].items() if value is not None}
    records = [item for item in records if item["id"].removeprefix("finding:") in labels]
    ranked = [labels[item["id"].removeprefix("finding:")] for item in records]
    positives = sum(labels.values())
    precision_at = {}
    for k in (5, 10, 20):
        top = ranked[:k]
        precision_at[f"precision@{k}"] = round(sum(top) / min(k, len(top)), 4)
    recall_at_20 = round(sum(ranked[:20]) / max(1, positives), 4)
    print(
        json.dumps(
            {
                "dataset": dataset["dataset"],
                "findings": len(labels),
                "positives": positives,
                "baseline": "severity heuristic",
                "precision": precision_at,
                "recall@20": recall_at_20,
                "ranking": [
                    {"id": item["id"], "severity": item["severity"], "label": labels[item["id"].removeprefix("finding:")]}
                    for item in records
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
