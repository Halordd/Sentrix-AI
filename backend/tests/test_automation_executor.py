from __future__ import annotations

import hashlib
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.automation import evaluate, sign_manifest
from app.automation_executor import ExecutorError, ReadOnlyExecutor, SafePocExecutor


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"sandbox-ok"
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


def manifest(target="127.0.0.1", **overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "engagementId": "executor-test",
        "authorizedBy": "user-admin",
        "validFrom": (now - timedelta(minutes=2)).isoformat(),
        "validUntil": (now + timedelta(minutes=20)).isoformat(),
        "targets": [target],
        "excludedTargets": [],
        "allowedActionClasses": ["READ_ONLY", "SAFE_POC"],
        "maxRiskTier": 1,
        "maxActions": 5,
        "maxDurationMinutes": 20,
        "snapshotRequired": True,
        "humanOnLoop": True,
    }
    payload.update(overrides)
    return sign_manifest(payload)


def test_read_only_executor_returns_evidence_hash(server):
    decision = evaluate(manifest(), "read.target_metadata", "127.0.0.1")
    result = ReadOnlyExecutor(timeout_seconds=2).execute(
        decision, f"127.0.0.1:{server}", allowed_hosts={"127.0.0.1"}
    )
    assert result.status == 200
    assert result.bytes_read == len(b"sandbox-ok")
    assert result.body_sha256 == hashlib.sha256(b"sandbox-ok").hexdigest()
    assert result.headers["content-type"] == "text/plain"


def test_safe_poc_reports_missing_security_headers(server):
    decision = evaluate(manifest(), "safe.poc_boundary_check", "127.0.0.1")
    result = SafePocExecutor(timeout_seconds=2).execute(
        decision, f"127.0.0.1:{server}", allowed_hosts={"127.0.0.1"}
    )
    assert result.status == 200
    assert result.observations["check"] == "security_headers"
    assert result.observations["nonDestructive"] is True
    assert "x-content-type-options" in result.observations["missing"]


def test_executor_rejects_non_r0_and_foreign_host(server):
    r1 = evaluate(manifest(), "safe.poc_boundary_check", "127.0.0.1")
    with pytest.raises(ExecutorError):
        ReadOnlyExecutor().execute(r1, f"127.0.0.1:{server}")

    r0 = evaluate(manifest(), "read.target_metadata", "127.0.0.1")
    with pytest.raises(ExecutorError):
        ReadOnlyExecutor().execute(
            r0, f"127.0.0.1:{server}", allowed_hosts={"10.20.20.20"}
        )
