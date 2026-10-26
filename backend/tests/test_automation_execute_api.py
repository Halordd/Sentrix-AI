from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app.automation import sign_manifest

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")
MIGRATOR_URL = "postgresql+psycopg://sentrix_migrator@10.20.10.20:5432/sentrix"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"execute-api-ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


@pytest.fixture()
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


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


def cleanup(candidate_id):
    engine = create_engine(MIGRATOR_URL)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
        try:
            connection.execute(
                text("DELETE FROM automation_execution WHERE candidate_id = :id"),
                {"id": candidate_id},
            )
            connection.execute(
                text("DELETE FROM automation_candidate WHERE id = :id"),
                {"id": candidate_id},
            )
            connection.execute(
                text("DELETE FROM audit_event WHERE resource_id = :id"), {"id": candidate_id}
            )
        finally:
            connection.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))


def test_r0_execution_api_captures_snapshots(server):
    token = admin_token()
    target = f"127.0.0.1:{server}"
    status, candidate = call(
        "/api/v1/automation/candidates",
        "POST",
        {
            "findingId": "finding-bola",
            "target": target,
            "actionCode": "read.target_metadata",
            "score": 0.9,
        },
        token,
    )
    assert status == 201, candidate
    candidate_id = candidate["id"]
    try:
        now = datetime.now(timezone.utc)
        manifest = sign_manifest(
            {
                "engagementId": f"exec-{uuid4().hex[:8]}",
                "authorizedBy": "user-admin",
                "validFrom": (now - timedelta(minutes=2)).isoformat(),
                "validUntil": (now + timedelta(minutes=20)).isoformat(),
                "targets": [target],
                "excludedTargets": [],
                "allowedActionClasses": ["READ_ONLY"],
                "maxRiskTier": 0,
                "maxActions": 5,
                "maxDurationMinutes": 20,
                "snapshotRequired": True,
                "humanOnLoop": True,
            }
        )
        status, execution = call(
            f"/api/v1/automation/candidates/{candidate_id}/execute",
            "POST",
            {"manifest": manifest},
            token,
        )
        assert status == 200, execution
        assert execution["httpStatus"] == 200
        assert execution["beforeHash"] == execution["afterHash"]
        assert execution["snapshotMismatch"] is False
    finally:
        cleanup(candidate_id)
