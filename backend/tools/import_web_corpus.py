"""Import the reviewed web corpus into an isolated DB schema.

Run only against the sentrix_corpus schema. It does not touch public tables.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import psycopg


def load_records(paths: list[Path]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        data = json.loads(path.read_text())
        records.extend(data["records"])
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dsn",
        default="postgresql://sentrix_migrator@10.20.10.20:5432/sentrix",
    )
    parser.add_argument("--scores", default="backend/training/web_graph/web_scores.json")
    parser.add_argument(
        "corpora",
        nargs="+",
        default=[
            "backend/training/web_graph/web_corpus_v2.json",
            "backend/training/web_graph/web_corpus_batch3.json",
        ],
    )
    args = parser.parse_args()
    records = load_records([Path(path) for path in args.corpora])
    scores = json.loads(Path(args.scores).read_text())
    project_id = "project-corpus-pilot"
    targets = {
        "juice-shop": "target-juice-shop",
        "webgoat": "target-webgoat",
    }
    with psycopg.connect(args.dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO corpus_pilot.project (id, name, status, scope)
                VALUES (%s, %s, 'ACTIVE', %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """,
                (project_id, "SENTRIX corpus pilot", "local lab; pilot only"),
            )
            for name, target_id in targets.items():
                cursor.execute(
                    """
                    INSERT INTO corpus_pilot.target (id, project_id, name, type, scope)
                    VALUES (%s, %s, %s, 'WEB', %s)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                    """,
                    (target_id, project_id, name, name),
                )
            for record in records:
                source_id = record["id"]
                target_key = "webgoat" if source_id.startswith("b3-") else "juice-shop"
                target_id = targets[target_key]
                finding_id = f"finding-{source_id}"
                score = scores.get(source_id, {}).get("score")
                if score is None:
                    score = 0.0
                action_code = (
                    "read.response_headers"
                    if record.get("cwe") == "CWE-693"
                    else "read.target_metadata"
                )
                cursor.execute(
                    """
                    INSERT INTO corpus_pilot.finding
                        (id, project_id, target_id, source_id, title, severity, status,
                         cwe, location, verified)
                    VALUES (%s, %s, %s, %s, %s, %s, 'NEW', %s, %s::jsonb, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        severity = EXCLUDED.severity,
                        cwe = EXCLUDED.cwe,
                        location = EXCLUDED.location,
                        verified = EXCLUDED.verified
                    """,
                    (
                        finding_id,
                        project_id,
                        target_id,
                        source_id,
                        record["title"],
                        record["severity"],
                        record.get("cwe"),
                        json.dumps(record.get("location") or {}),
                        bool(record.get("label") == 1),
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO corpus_pilot.candidate
                        (id, finding_id, target, action_code, score, status, model)
                    VALUES (%s, %s, %s, %s, %s, 'QUEUED', %s)
                    ON CONFLICT (id) DO UPDATE SET
                        score = EXCLUDED.score,
                        action_code = EXCLUDED.action_code,
                        target = EXCLUDED.target
                    """,
                    (
                        f"candidate-{source_id}",
                        finding_id,
                        target_key,
                        action_code,
                        score,
                        "HeteroConv-SAGE pilot",
                    ),
                )
        connection.commit()
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM corpus_pilot.finding")
            findings = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM corpus_pilot.candidate")
            candidates = cursor.fetchone()[0]
            cursor.execute(
                "SELECT target_id, count(*) FROM corpus_pilot.finding GROUP BY target_id ORDER BY target_id"
            )
            by_target = cursor.fetchall()
    print(
        json.dumps(
            {
                "project": project_id,
                "findings": findings,
                "candidates": candidates,
                "byTarget": {target: count for target, count in by_target},
                "scores": len(scores),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
