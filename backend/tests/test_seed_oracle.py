from __future__ import annotations

import pytest
from sqlalchemy import text

from app.db import get_engine

EXPECTED = {
    "scan_profile": 3,
    "app_user": 5,
    "project": 3,
    "project_member": 3,
    "target": 4,
    "target_authorization": 3,
    "scan_job": 3,
    "scan_run": 3,
    "scan_observation": 0,
    "finding": 3,
    "evidence": 3,
    "finding_status_event": 3,
    "analysis": 1,
    "prompt_template": 1,
    "prompt_template_version": 1,
    "model": 2,
    "model_version": 2,
    "dataset": 1,
    "dataset_version": 1,
    "evaluation_run": 0,
    "remediation": 1,
    "verification": 0,
    "report": 1,
    "report_finding": 2,
    "audit_event": 2,
}

FIXED_IDS = {
    "app_user": ["user-maya", "user-jon", "user-priya", "user-admin", "user-system"],
    "project": ["project-atlas", "project-helix", "project-northstar"],
    "target": ["target-atlas-api", "target-atlas-web", "target-helix-api", "target-northstar"],
    "finding": ["finding-bola", "finding-bucket", "finding-debug"],
    "report": ["report-atlas"],
    "analysis": ["analysis-bola"],
    "remediation": ["task-bola"],
}


@pytest.fixture(scope="module")
def connection():
    with get_engine().connect() as connection:
        yield connection


M7_ADDITIONS = {
    "model": 1,
    "model_version": 1,
    "dataset": 1,
    "dataset_version": 1,
    "evaluation_run": 1,
}


def test_total_seed_rows_is_51_plus_optional_m7():
    with get_engine().connect() as connection:
        counts = {
            table: connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in EXPECTED
        }
    m7_present = counts["evaluation_run"] == 1
    audit_extra = counts["audit_event"] - EXPECTED["audit_event"]
    assert audit_extra >= 0, f"audit_event: {counts['audit_event']} < seed baseline"
    for table, expected in EXPECTED.items():
        if table == "audit_event":
            continue
        allowed = expected + (M7_ADDITIONS.get(table, 0) if m7_present else 0)
        assert counts[table] == allowed, f"{table}: {counts[table]} != {allowed}"
    total = sum(counts.values()) - audit_extra
    assert total == 51 + (sum(M7_ADDITIONS.values()) if m7_present else 0)


def test_fixed_ids_exist(connection):
    for table, ids in FIXED_IDS.items():
        actual = {
            row[0]
            for row in connection.execute(
                text(f"SELECT id FROM {table} WHERE id = ANY(:ids)"),
                {"ids": ids},
            )
        }
        assert actual == set(ids), f"{table}: {actual}"


def test_seed_is_deterministic_order(connection):
    findings = [
        row[0]
        for row in connection.execute(
            text("SELECT id FROM finding ORDER BY created_at DESC, id")
        )
    ]
    assert findings == ["finding-bola", "finding-bucket", "finding-debug"]
