from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")


def login() -> str:
    request = urllib.request.Request(
        API + "/api/v1/auth/login",
        data=json.dumps(
            {"email": "maya@sentrix.local", "password": "sentrix-demo"}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read())["token"]
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"API not reachable: {exc}")


def test_completed_scan_cannot_run():
    token = login()
    request = urllib.request.Request(
        API + "/api/v1/scans/scan-atlas/run",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=8)
    except urllib.error.HTTPError as error:
        assert error.code == 409
        body = json.loads(error.read())
        assert "can run" in body["detail"]
    else:
        raise AssertionError("completed scan was allowed to run")


def test_verification_requires_verifiable_finding_state():
    token = login()
    request = urllib.request.Request(
        API + "/api/v1/remediations/task-bola/verify",
        data=json.dumps({"outcome": "VERIFIED", "method": "MANUAL_REVIEW"}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=8)
    except urllib.error.HTTPError as error:
        assert error.code == 409
        body = json.loads(error.read())
        assert "does not allow" in body["detail"]
    else:
        raise AssertionError("verification was allowed on a CONFIRMED finding")
