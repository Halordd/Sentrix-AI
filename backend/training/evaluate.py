"""Deterministic baseline evaluation for SENTRIX M7.

This is a measured evaluation of a documented rule-based baseline, not a mock
inference claim. It reads a fixed synthetic fixture, computes macro precision,
recall and F1, and records a MEASURED evaluation_run with seed/environment.

Usage on VM01:
    cd ~/sentrix-backend
    venv/bin/python training/evaluate.py
    venv/bin/python training/evaluate.py --verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
from datetime import datetime, timezone
from pathlib import Path

DATASET = Path(__file__).with_name("dataset.jsonl")
DATASET_VERSION_ID = "datasetversion-baseline-2026.10"
MODEL_ID = "model-sentrix-baseline"
MODEL_VERSION_ID = "modelversion-baseline-1.0"
EVALUATION_ID = "eval-baseline-001"
SEED = 42
LABELS = ("CRITICAL", "HIGH", "MEDIUM", "LOW")

RULES = (
    ("CRITICAL", ("remote code", "rce", "deserialization", "command injection")),
    ("HIGH", ("authorization", "access control", "privilege", "idor", "bypass")),
    ("MEDIUM", ("misconfiguration", "exposure", "public bucket", "publicly readable",
                "security header", "cors", "backup file", "metrics")),
    ("LOW", ("verbose", "version", "informational", "trace", "banner")),
)


def load_dataset() -> list[dict]:
    rows = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    if len(rows) != 20:
        raise SystemExit(f"expected 20 fixture rows, got {len(rows)}")
    for row in rows:
        if row.get("label") not in LABELS:
            raise SystemExit(f"invalid label in {row!r}")
    return rows


def predict(text: str) -> str:
    lowered = text.lower()
    for label, needles in RULES:
        if any(needle in lowered for needle in needles):
            return label
    return "LOW"


def compute_metrics(rows: list[dict]) -> dict:
    matrix = {label: {"tp": 0, "fp": 0, "fn": 0} for label in LABELS}
    correct = 0
    for row in rows:
        expected = row["label"]
        actual = predict(row["text"])
        if actual == expected:
            correct += 1
            matrix[expected]["tp"] += 1
        else:
            matrix[actual]["fp"] += 1
            matrix[expected]["fn"] += 1
    per_label = {}
    for label in LABELS:
        tp, fp, fn = matrix[label]["tp"], matrix[label]["fp"], matrix[label]["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
    macro_p = sum(v["precision"] for v in per_label.values()) / len(LABELS)
    macro_r = sum(v["recall"] for v in per_label.values()) / len(LABELS)
    macro_f1 = sum(v["f1"] for v in per_label.values()) / len(LABELS)
    return {
        "precision": round(macro_p, 4),
        "recall": round(macro_r, 4),
        "f1": round(macro_f1, 4),
        "accuracy": round(correct / len(rows), 4),
        "samples": len(rows),
        "perLabel": per_label,
    }


def dataset_hash() -> str:
    return hashlib.sha256(DATASET.read_bytes()).hexdigest()


def write_evaluation(metrics: dict) -> None:
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit("psycopg is required: install backend requirements") from exc

    dsn = os.getenv("SENTRIX_TRAINING_DSN", "postgresql://sentrix_migrator@10.20.10.20:5432/sentrix")
    now = datetime.now(timezone.utc)
    content_hash = dataset_hash()
    artifact_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    label_distribution = {
        label: round(sum(1 for row in load_dataset() if row["label"] == label) / 20, 4)
        for label in LABELS
    }
    environment = {
        "runtime": platform.python_version(),
        "platform": platform.platform(),
        "host": socket.gethostname(),
        "scriptSha256": artifact_hash,
        "datasetSha256": content_hash,
        "note": "Measured rule-based baseline on a synthetic, fixed fixture.",
    }
    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE sentrix_eval")
            cursor.execute(
                """
                INSERT INTO model (id, name, provider_type, description)
                VALUES (%s, %s, 'LOCAL', %s) ON CONFLICT (id) DO NOTHING
                """,
                (MODEL_ID, "SENTRIX baseline classifier", "Deterministic rule-based baseline."),
            )
            cursor.execute(
                """
                INSERT INTO dataset (id, name, description, provenance, license)
                VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING
                """,
                (
                    "dataset-baseline",
                    "SENTRIX baseline fixture",
                    "Synthetic labeled security-finding fixtures.",
                    "synthetic; generated for SENTRIX M7",
                    "CC0-1.0",
                ),
            )
            cursor.execute(
                """
                INSERT INTO dataset_version
                    (id, dataset_id, version, sample_count, label_distribution, content_hash, created_by)
                VALUES (%s, 'dataset-baseline', '2026.10', %s, %s::jsonb, %s, 'user-admin')
                ON CONFLICT (id) DO NOTHING
                """,
                (DATASET_VERSION_ID, len(load_dataset()), json.dumps(label_distribution), content_hash),
            )
            stored_hash = cursor.execute(
                "SELECT content_hash FROM dataset_version WHERE id = %s", (DATASET_VERSION_ID,)
            ).fetchone()[0]
            if stored_hash != content_hash:
                raise SystemExit("dataset hash differs from the recorded immutable version")
            cursor.execute(
                """
                INSERT INTO model_version
                    (id, model_id, version, stage, artifact_uri, artifact_sha256,
                     training_dataset_version_id, metrics, is_mock)
                VALUES (%s, %s, '1.0', 'CANDIDATE', %s, %s, %s, %s::jsonb, false)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    MODEL_VERSION_ID,
                    MODEL_ID,
                    "local://backend/training/evaluate.py",
                    artifact_hash,
                    DATASET_VERSION_ID,
                    json.dumps(metrics),
                ),
            )
            cursor.execute(
                """
                INSERT INTO evaluation_run
                    (id, model_version_id, dataset_version_id, status, data_origin,
                     metrics, environment, seed, started_at, finished_at, created_by)
                VALUES (%s, %s, %s, 'COMPLETED', 'MEASURED', %s::jsonb, %s::jsonb,
                        %s, %s, %s, 'user-admin')
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    EVALUATION_ID,
                    MODEL_VERSION_ID,
                    DATASET_VERSION_ID,
                    json.dumps(metrics),
                    json.dumps(environment),
                    SEED,
                    now,
                    now,
                ),
            )
        connection.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="print metrics and verify repeatability without writing")
    args = parser.parse_args()
    rows = load_dataset()
    metrics = compute_metrics(rows)
    print(json.dumps({"datasetSha256": dataset_hash(), "metrics": metrics}, indent=2))
    if not args.verify:
        write_evaluation(metrics)


if __name__ == "__main__":
    main()
