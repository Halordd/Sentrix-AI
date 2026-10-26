from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")
MIGRATOR_URL = "postgresql+psycopg://sentrix_migrator@10.20.10.20:5432/sentrix"
TOKEN = ""


def call(path: str, method: str = "GET", payload: dict | None = None):
    headers = {"Accept": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")
    except (OSError, urllib.error.URLError) as error:
        pytest.skip(f"API not reachable: {error}")


def login() -> None:
    global TOKEN
    status, body = call(
        "/api/v1/auth/login",
        "POST",
        {"email": "maya@sentrix.local", "password": "sentrix-demo"},
    )
    assert status == 200
    TOKEN = body["token"]


def cleanup(ids: dict) -> None:
    engine = create_engine(MIGRATOR_URL)
    with engine.begin() as connection:
        if ids.get("report"):
            connection.execute(text("DELETE FROM report_finding WHERE report_id = :id"), {"id": ids["report"]})
            connection.execute(text("DELETE FROM report WHERE id = :id"), {"id": ids["report"]})
        if ids.get("remediation"):
            connection.execute(text("DELETE FROM verification WHERE remediation_id = :id"), {"id": ids["remediation"]})
            connection.execute(text("DELETE FROM remediation WHERE id = :id"), {"id": ids["remediation"]})
        if ids.get("analysis"):
            connection.execute(text("DELETE FROM analysis WHERE id = :id"), {"id": ids["analysis"]})
        if ids.get("finding"):
            connection.execute(text("ALTER TABLE finding_status_event DISABLE TRIGGER USER"))
            try:
                connection.execute(
                    text("DELETE FROM finding_status_event WHERE finding_id = :id"),
                    {"id": ids["finding"]},
                )
            finally:
                connection.execute(text("ALTER TABLE finding_status_event ENABLE TRIGGER USER"))
            connection.execute(text("DELETE FROM evidence WHERE finding_id = :id"), {"id": ids["finding"]})
            connection.execute(text("DELETE FROM finding WHERE id = :id"), {"id": ids["finding"]})
        if ids.get("scan"):
            connection.execute(text("DELETE FROM scan_run WHERE job_id = :id"), {"id": ids["scan"]})
            connection.execute(text("DELETE FROM scan_job WHERE id = :id"), {"id": ids["scan"]})
        if ids.get("target"):
            connection.execute(text("DELETE FROM target_authorization WHERE target_id = :id"), {"id": ids["target"]})
            connection.execute(text("DELETE FROM target WHERE id = :id"), {"id": ids["target"]})
        if ids.get("project"):
            connection.execute(text("DELETE FROM project WHERE id = :id"), {"id": ids["project"]})
        audit_ids = [
            value
            for key, value in ids.items()
            if key in {"project", "target", "scan", "finding", "remediation", "report"}
        ]
        if audit_ids:
            connection.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
            try:
                connection.execute(
                    text("DELETE FROM audit_event WHERE resource_id = ANY(:ids)"),
                    {"ids": audit_ids},
                )
            finally:
                connection.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))


def test_full_mutation_workflow():
    login()
    suffix = uuid4().hex[:8]
    ids: dict[str, str] = {}
    try:
        status, project = call(
            "/api/v1/projects",
            "POST",
            {"name": f"Mutation Project {suffix}", "scope": "local test"},
        )
        assert status == 201
        ids["project"] = project["id"]

        status, target = call(
            "/api/v1/targets",
            "POST",
            {
                "projectId": ids["project"],
                "name": f"mutation-{suffix}.local",
                "type": "API",
                "scope": f"https://mutation-{suffix}.local/*",
                "authorizationConfirmed": True,
            },
        )
        assert status == 201
        ids["target"] = target["id"]

        status, scan = call(
            "/api/v1/scans",
            "POST",
            {"targetId": ids["target"], "name": f"Mutation Scan {suffix}", "profile": "API authorization"},
        )
        assert status == 201
        ids["scan"] = scan["id"]

        status, result = call(f"/api/v1/scans/{ids['scan']}/run", "POST", {})
        assert status == 200
        ids["finding"] = result["finding"]["id"]
        assert result["finding"]["title"] == "Demo configuration exposure"
        assert result["finding"]["severity"] == "Low"
        assert result["finding"]["status"] == "New"

        status, _ = call(
            f"/api/v1/findings/{ids['finding']}/status",
            "PATCH",
            {"status": "IN_PROGRESS"},
        )
        assert status == 200

        status, analysis = call(f"/api/v1/findings/{ids['finding']}/analyses", "POST", {})
        assert status == 201
        ids["analysis"] = analysis["id"]
        assert analysis["confidence"] == 76
        assert analysis["model"] == "SENTRIX Risk Engine"
        assert analysis["simulated"] is True

        status, task = call(
            f"/api/v1/findings/{ids['finding']}/remediations",
            "POST",
            {"assignee": "Maya Chen", "dueDate": "2026-10-25", "notes": "mutation test"},
        )
        assert status == 201
        ids["remediation"] = task["id"]

        status, _ = call(
            f"/api/v1/remediations/{ids['remediation']}/verify",
            "POST",
            {"outcome": "VERIFIED", "method": "MANUAL_REVIEW", "notes": "mutation test"},
        )
        assert status == 200

        status, report = call(
            "/api/v1/reports",
            "POST",
            {"projectId": ids["project"], "title": f"Mutation Report {suffix}", "scanId": ids["scan"]},
        )
        assert status == 201
        ids["report"] = report["id"]

        status, _ = call(f"/api/v1/reports/{ids['report']}/publish", "POST", {})
        assert status == 200
    finally:
        cleanup(ids)
