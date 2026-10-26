from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app.automation import sign_manifest

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


def admin_token():
    status, body = call(
        "/api/v1/auth/login",
        "POST",
        {"email": "admin@sentrix.local", "password": "admin-demo"},
    )
    assert status == 200, body
    return body["token"]


def cleanup(candidate_id, request_id):
    engine = create_engine(MIGRATOR_URL)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
        try:
            if request_id:
                connection.execute(
                    text("DELETE FROM automation_request WHERE id = :id"), {"id": request_id}
                )
            if candidate_id:
                connection.execute(
                    text("DELETE FROM automation_candidate WHERE id = :id"),
                    {"id": candidate_id},
                )
            ids = [value for value in (candidate_id, request_id) if value]
            if ids:
                connection.execute(
                    text("DELETE FROM audit_event WHERE resource_id = ANY(:ids)"),
                    {"ids": ids},
                )
        finally:
            connection.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))


def test_r2_request_requires_approval_then_can_be_approved():
    token = admin_token()
    candidate_id = None
    request_id = None
    try:
        status, candidate = call(
            "/api/v1/automation/candidates",
            "POST",
            {
                "findingId": "finding-bola",
                "target": "10.20.20.20",
                "actionCode": "state.change_user",
                "score": 0.91,
            },
            token,
        )
        assert status == 201, candidate
        candidate_id = candidate["id"]

        now = datetime.now(timezone.utc)
        manifest = sign_manifest(
            {
                "engagementId": f"r2-{uuid4().hex[:8]}",
                "authorizedBy": "user-admin",
                "validFrom": (now - timedelta(minutes=2)).isoformat(),
                "validUntil": (now + timedelta(minutes=20)).isoformat(),
                "targets": ["10.20.20.20"],
                "excludedTargets": [],
                "allowedActionClasses": ["READ_ONLY", "SAFE_POC", "STATE_CHANGING"],
                "maxRiskTier": 2,
                "maxActions": 5,
                "maxDurationMinutes": 20,
                "snapshotRequired": True,
                "humanOnLoop": True,
            }
        )

        status, request = call(
            f"/api/v1/automation/candidates/{candidate_id}/request",
            "POST",
            {"manifest": manifest},
            token,
        )
        assert status == 201, request
        request_id = request["requestId"]
        assert request["status"] == "PENDING"

        status, approved = call(
            f"/api/v1/automation/requests/{request_id}/approve",
            "POST",
            {"reason": "lab approval"},
            token,
        )
        assert status == 200, approved
        assert approved["status"] == "APPROVED"

        status, candidates = call("/api/v1/automation/candidates", token=token)
        assert status == 200
        row = next(item for item in candidates["candidates"] if item["id"] == candidate_id)
        assert row["status"] == "APPROVED"
    finally:
        cleanup(candidate_id, request_id)
