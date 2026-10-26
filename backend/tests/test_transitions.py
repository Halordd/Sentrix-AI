from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")
TOKEN = ""


def login() -> None:
    global TOKEN
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
            TOKEN = json.loads(response.read())["token"]
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"API not reachable: {exc}")


def transition(finding_id: str, target: str, reason: str | None = None):
    login()
    body = {"to": target}
    if reason is not None:
        body["reason"] = reason
    request = urllib.request.Request(
        API + f"/api/v1/findings/{finding_id}/transitions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


@pytest.mark.parametrize(
    "finding_id,target,reason",
    [
        ("finding-bola", "IN_PROGRESS", None),
        ("finding-bola", "RESOLVED", "not allowed through transition"),
        ("finding-bola", "CONFIRMED", None),
        ("finding-bucket", "IN_PROGRESS", None),
        ("finding-bucket", "RESOLVED", None),
        ("finding-debug", "IN_PROGRESS", None),
    ],
)
def test_forbidden_transitions(finding_id, target, reason):
    status, body = transition(finding_id, target, reason)
    assert status == 409, body
    assert "cannot move" in body["detail"] or "verification" in body["detail"]


def test_reason_required_for_accepted_risk():
    status, body = transition("finding-bola", "ACCEPTED_RISK")
    assert status == 422
    assert body["detail"] == "reason is required"
