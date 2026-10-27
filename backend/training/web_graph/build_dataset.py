"""Build a heterogeneous graph dataset from reviewed web/API corpus records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def infer_target(records: list[dict]) -> tuple[str, str]:
    if any(record.get("id", "").startswith("b3-") for record in records):
        return "target:webgoat", "WebGoat lab"
    return "target:juice-shop", "Juice Shop lab"


def build(
    corpus: dict,
    target_id: str,
    target_name: str,
    reviewed_only: bool = False,
) -> dict:
    records = corpus["records"]
    if reviewed_only:
        records = [
            record
            for record in records
            if record.get("reviewStatus") in {"HUMAN_VERIFIED", "HUMAN_REJECTED"}
        ]
    nodes: list[dict] = [{"id": target_id, "type": "Target", "name": target_name}]
    edges: list[dict] = []
    labels: dict[str, int | None] = {}
    seen_endpoints: set[str] = set()
    seen_cwes: set[str] = set()
    for record in records:
        path = record["location"]["value"]
        endpoint_id = f"endpoint:{path}"
        if endpoint_id not in seen_endpoints:
            seen_endpoints.add(endpoint_id)
            nodes.append({"id": endpoint_id, "type": "Endpoint", "path": path})
        finding_id = f"finding:{record['id']}"
        nodes.append(
            {
                "id": finding_id,
                "type": "Finding",
                "title": record["title"],
                "severity": record["severity"],
                "source": record["source"],
                "cwe": record["cwe"],
            }
        )
        labels[record["id"]] = None if record.get("label") is None else int(record["label"])
        edges.append({"source": target_id, "target": endpoint_id, "type": "EXPOSES"})
        edges.append({"source": endpoint_id, "target": finding_id, "type": "HAS_FINDING"})
        cwe_id = f"cwe:{record['cwe']}"
        if cwe_id not in seen_cwes:
            seen_cwes.add(cwe_id)
            nodes.append({"id": cwe_id, "type": "CWE", "cwe": record["cwe"]})
        edges.append({"source": finding_id, "target": cwe_id, "type": "HAS_CWE"})
        evidence_id = f"evidence:{record['id']}"
        nodes.append(
            {
                "id": evidence_id,
                "type": "Evidence",
                "status": record["evidence"]["status"],
                "bodySha256": record["evidence"]["bodySha256"],
            }
        )
        edges.append({"source": finding_id, "target": evidence_id, "type": "HAS_EVIDENCE"})
        if record.get("reviewStatus") == "HUMAN_VERIFIED":
            verification_id = f"verification:{record['id']}"
            nodes.append({"id": verification_id, "type": "Verification", "outcome": "VERIFIED"})
            edges.append({"source": finding_id, "target": verification_id, "type": "VERIFIED_BY"})
    return {
        "dataset": "sentrix-web-lab-corpus",
        "source": corpus.get("base"),
        "target": {"id": target_id, "name": target_name},
        "labels": labels,
        "nodes": nodes,
        "edges": edges,
        "counts": {
            "findings": len(labels),
            "verified": sum(1 for value in labels.values() if value == 1),
            "human_rejected": sum(1 for value in labels.values() if value == 0),
            "pending_review": sum(1 for value in labels.values() if value is None),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", nargs="?", default="web_corpus.json")
    parser.add_argument("--out", default="web_dataset.json")
    parser.add_argument("--target-id", default="")
    parser.add_argument("--target-name", default="")
    parser.add_argument("--reviewed-only", action="store_true")
    args = parser.parse_args()
    corpus = json.loads(Path(args.corpus).read_text())
    inferred_id, inferred_name = infer_target(corpus["records"])
    dataset = build(
        corpus,
        target_id=args.target_id or inferred_id,
        target_name=args.target_name or inferred_name,
        reviewed_only=args.reviewed_only,
    )
    Path(args.out).write_text(json.dumps(dataset, indent=2))
    print(json.dumps({"output": args.out, **dataset["counts"]}, indent=2))


if __name__ == "__main__":
    main()
