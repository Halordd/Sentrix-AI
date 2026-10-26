from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")
WEB = os.getenv("SENTRIX_WEB", "http://10.20.10.10")


def login() -> str:
    req = urllib.request.Request(
        API + "/api/v1/auth/login",
        data=json.dumps(
            {"email": "maya@sentrix.local", "password": "sentrix-demo"}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            return json.loads(response.read())["token"]
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"API not reachable: {exc}")


def fetch(path: str, token: str) -> str:
    request = urllib.request.Request(
        API + path, headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return response.read().decode()


def test_api_payloads_have_no_secret_material():
    token = login()
    payloads = [
        fetch("/api/v1/bootstrap", token),
        fetch("/api/v1/auth/me", token),
    ]
    for payload in payloads:
        assert "password_hash" not in payload
        assert "pbkdf2_sha256" not in payload
        assert "sentrix-demo" not in payload
        assert "admin-demo" not in payload
        assert "postgresql" not in payload
        assert "SENTRIX_SECRET_KEY" not in payload


def test_frontend_bundle_has_no_password_literals():
    for path in ("/app.js", "/api.js", "/login.html"):
        with urllib.request.urlopen(WEB + path, timeout=8) as response:
            if response.status != 200:
                continue
            body = response.read().decode()
        for secret in ("sentrix-demo", "admin-demo", "SENTRIX_SECRET_KEY", "password_hash"):
            assert secret not in body, f"{secret} leaked in {path}"
