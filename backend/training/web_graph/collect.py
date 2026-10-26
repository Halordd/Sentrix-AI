"""Collect the current SENTRIX web/API entities into a graph JSON.

This is the data-collection seam for a future heterogeneous GNN. It uses only
existing tables; CWE/location fields are added in a later migration.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dsn",
        default=os.getenv(
            "SENTRIX_TRAINING_DSN",
            "postgresql://sentrix_migrator@10.20.10.20:5432/sentrix",
        ),
    )
    parser.add_argument("--out", default=str(Path.home() / "sentrix-gnn/web_graph.json"))
    args = parser.parse_args()

    with psycopg.connect(args.dsn) as connection:
        with connection.cursor() as cursor:
            projects = cursor.execute(
                "SELECT id, name, status, scope FROM project ORDER BY id"
            ).fetchall()
            targets = cursor.execute(
                "SELECT id, project_id, name, type, scope FROM target ORDER BY id"
            ).fetchall()
            findings = cursor.execute(
                """
                SELECT id, project_id, target_id, title, severity, status, source,
                       cwe, location
                FROM finding ORDER BY id
                """
            ).fetchall()
            evidence = cursor.execute(
                "SELECT id, finding_id, kind, title, sha256 FROM evidence ORDER BY id"
            ).fetchall()
            verifications = cursor.execute(
                "SELECT id, finding_id, outcome, method FROM verification ORDER BY id"
            ).fetchall()

    nodes = []
    edges = []
    for project_id, name, status, scope in projects:
        nodes.append({"id": f"project:{project_id}", "type": "Project", "name": name, "status": status})
    for target_id, project_id, name, target_type, scope in targets:
        nodes.append(
            {
                "id": f"target:{target_id}",
                "type": "Target",
                "name": name,
                "targetType": target_type,
                "scope": scope,
            }
        )
        edges.append({"source": f"project:{project_id}", "target": f"target:{target_id}", "type": "HAS_TARGET"})
    for finding_id, project_id, target_id, title, severity, status, source, cwe, location in findings:
        nodes.append(
            {
                "id": f"finding:{finding_id}",
                "type": "Finding",
                "title": title,
                "severity": severity,
                "status": status,
                "source": source,
                "cwe": cwe,
                "location": location or {},
            }
        )
        edges.append({"source": f"target:{target_id}", "target": f"finding:{finding_id}", "type": "HAS_FINDING"})
    for evidence_id, finding_id, kind, title, sha256 in evidence:
        nodes.append(
            {
                "id": f"evidence:{evidence_id}",
                "type": "Evidence",
                "kind": kind,
                "title": title,
                "sha256": sha256,
            }
        )
        edges.append(
            {"source": f"finding:{finding_id}", "target": f"evidence:{evidence_id}", "type": "HAS_EVIDENCE"}
        )
    for verification_id, finding_id, outcome, method in verifications:
        nodes.append(
            {
                "id": f"verification:{verification_id}",
                "type": "Verification",
                "outcome": outcome,
                "method": method,
            }
        )
        edges.append(
            {
                "source": f"finding:{finding_id}",
                "target": f"verification:{verification_id}",
                "type": "VERIFIED_BY",
            }
        )

    labels = {
        item["id"].removeprefix("finding:"): (
            1
            if any(
                edge["source"] == item["id"] and edge["type"] == "VERIFIED_BY"
                for edge in edges
            )
            else 0
        )
        for item in nodes
        if item["type"] == "Finding"
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"nodes": nodes, "edges": edges, "labels": labels}, indent=2))
    print(
        json.dumps(
            {
                "output": str(out),
                "nodes": len(nodes),
                "edges": len(edges),
                "findings": len(labels),
                "verified_labels": sum(labels.values()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
