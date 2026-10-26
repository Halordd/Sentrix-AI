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


def call(path, method="GET", payload=None, token=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else None
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"API not reachable: {exc}")


def login():
    status, body = call(
        "/api/v1/auth/login",
        "POST",
        {"email": "maya@sentrix.local", "password": "sentrix-demo"},
    )
    assert status == 200, body
    return body["token"]


def cleanup(ids):
    engine = create_engine(MIGRATOR_URL)
    with engine.begin() as connection:
        if ids.get("scan"):
            connection.execute(text("DELETE FROM scan_run WHERE job_id = :id"), {"id": ids["scan"]})
            connection.execute(text("DELETE FROM scan_job WHERE id = :id"), {"id": ids["scan"]})
        if ids.get("target"):
            connection.execute(text("DELETE FROM target_authorization WHERE target_id = :id"), {"id": ids["target"]})
            connection.execute(text("DELETE FROM target WHERE id = :id"), {"id": ids["target"]})
        if ids.get("project"):
            connection.execute(text("DELETE FROM project WHERE id = :id"), {"id": ids["project"]})
        audit_ids = [v for k, v in ids.items() if k in {"project", "target", "scan"}]
        if audit_ids:
            connection.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
            try:
                connection.execute(
                    text("DELETE FROM audit_event WHERE resource_id = ANY(:ids)"),
                    {"ids": audit_ids},
                )
            finally:
                connection.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))


def test_stale_claimed_run_is_recovered():
    token = login()
    suffix = uuid4().hex[:8]
    ids = {}
    try:
        status, project = call("/api/v1/projects", "POST", {"name": f"Recovery {suffix}", "scope": "local"}, token)
        assert status == 201
        ids["project"] = project["id"]

        status, target = call(
            "/api/v1/targets",
            "POST",
            {
                "projectId": ids["project"],
                "name": f"recovery-{suffix}.local",
                "type": "API",
                "scope": f"https://recovery-{suffix}.local/*",
                "authorizationConfirmed": True,
            },
            token,
        )
        assert status == 201
        ids["target"] = target["id"]

        status, scan = call(
            "/api/v1/scans",
            "POST",
            {"targetId": ids["target"], "name": f"Recovery {suffix}", "profile": "API authorization"},
            token,
        )
        assert status == 201
        ids["scan"] = scan["id"]

        status, claim = call("/api/v1/worker/claims", "POST", {}, token)
        assert status == 200
        assert claim["job"]["id"] == ids["scan"]

        engine = create_engine(MIGRATOR_URL)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE scan_run SET heartbeat_at = now() - interval '10 minutes' WHERE id = :id"
                ),
                {"id": claim["runId"]},
            )

        status, recovered = call("/api/v1/worker/recover", "POST", {}, token)
        assert status == 200
        assert claim["runId"] in recovered["recovered"]

        with engine.connect() as connection:
            run_status = connection.execute(
                text("SELECT status FROM scan_run WHERE id = :id"),
                {"id": claim["runId"]},
            ).scalar_one()
            job_status = connection.execute(
                text("SELECT status FROM scan_job WHERE id = :id"),
                {"id": ids["scan"]},
            ).scalar_one()
        assert run_status == "FAILED"
        assert job_status == "FAILED"
    finally:
        cleanup(ids)
