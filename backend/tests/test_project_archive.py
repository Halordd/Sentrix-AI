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
        connection.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
        try:
            if ids.get("target"):
                connection.execute(
                    text("DELETE FROM target_authorization WHERE target_id = :id"),
                    {"id": ids["target"]},
                )
                connection.execute(text("DELETE FROM target WHERE id = :id"), {"id": ids["target"]})
            if ids.get("project"):
                connection.execute(text("DELETE FROM project WHERE id = :id"), {"id": ids["project"]})
            audit_ids = [v for k, v in ids.items() if k in {"project", "target"}]
            connection.execute(
                text("DELETE FROM audit_event WHERE resource_id = ANY(:ids)"),
                {"ids": audit_ids},
            )
        finally:
            connection.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))


def test_archived_project_is_rejected_for_new_scans():
    token = login()
    suffix = uuid4().hex[:8]
    ids = {}
    try:
        status, project = call(
            "/api/v1/projects", "POST", {"name": f"Archive {suffix}", "scope": "local"}, token
        )
        assert status == 201
        ids["project"] = project["id"]

        status, target = call(
            "/api/v1/targets",
            "POST",
            {
                "projectId": ids["project"],
                "name": f"archive-{suffix}.local",
                "type": "API",
                "scope": f"https://archive-{suffix}.local/*",
                "authorizationConfirmed": True,
            },
            token,
        )
        assert status == 201
        ids["target"] = target["id"]

        status, archived = call(
            f"/api/v1/projects/{ids['project']}/archive", "POST", {}, token
        )
        assert status == 200, archived
        assert archived["status"] == "Archived"

        status, blocked = call(
            "/api/v1/scans",
            "POST",
            {"targetId": ids["target"], "name": "blocked", "profile": "API authorization"},
            token,
        )
        assert status == 409, blocked
        assert "archived" in blocked["detail"]
    finally:
        cleanup(ids)
