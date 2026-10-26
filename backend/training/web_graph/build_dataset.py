"""Build a heterogeneous graph dataset from the 20-record web corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build(corpus: dict) -> dict:
    nodes: list[dict] = [{"id": "target:lab", "type": "Target", "name": "Juice Shop lab"}]
    edges: list[dict] = []
    labels: dict[str, int] = {}
    seen_endpoints = set()
    seen_cwes = set()
    for record in corpus["records"]:
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
        edges.append({"source": "target:lab", "target": endpoint_id, "type": "EXPOSES"})
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
        if record["label"]:
            verification_id = f"verification:{record['id']}"
            nodes.append({"id": verification_id, "type": "Verification", "outcome": "VERIFIED"})
            edges.append({"source": finding_id, "target": verification_id, "type": "VERIFIED_BY"})
    return {
        "dataset": "sentrix-web-lab-corpus",
        "source": corpus.get("base"),
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
    args = parser.parse_args()
    corpus = json.loads(Path(args.corpus).read_text())
    dataset = build(corpus)
    Path(args.out).write_text(json.dumps(dataset, indent=2))
    print(json.dumps({"output": args.out, **dataset["counts"]}, indent=2))


if __name__ == "__main__":
    main()
