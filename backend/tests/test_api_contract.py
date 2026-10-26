from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")
TOKEN = ""


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


def get(path: str, authenticated: bool = True):
    headers = {"Accept": "application/json", **auth_headers()}
    try:
        with urllib.request.urlopen(
            urllib.request.Request(API + path, headers=headers), timeout=5
        ) as response:
            return response.status, json.loads(response.read())
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"API not reachable: {exc}")


def ensure_token() -> None:
    global TOKEN
    if TOKEN:
        return
    try:
        request = urllib.request.Request(
            API + "/api/v1/auth/login",
            data=json.dumps(
                {"email": "maya@sentrix.local", "password": "sentrix-demo"}
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            TOKEN = json.loads(response.read())["token"]
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"API not reachable: {exc}")


def test_health():
    status, body = get("/health", authenticated=False)
    assert status == 200
    assert body == {"status": "ok", "service": "sentrix-api"}


def test_database_health():
    status, body = get("/health/db", authenticated=False)
    assert status == 200
    assert body["database"] == "sentrix"


def test_bootstrap_requires_authentication():
    request = urllib.request.Request(API + "/api/v1/bootstrap")
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=5)
    assert error.value.code == 401


def test_bootstrap_contract():
    ensure_token()
    status, body = get("/api/v1/bootstrap")
    assert status == 200
    assert len(body["projects"]) == 3
    assert len(body["findings"]) == 3
    assert len(body["reports"]) == 1
    assert len(body["analyses"]) == 1


def test_scan_profiles():
    ensure_token()
    status, body = get("/api/v1/scan-profiles")
    assert status == 200
    assert {row["id"] for row in body} == {
        "external_attack_surface",
        "api_authorization",
        "cloud_configuration",
    }
