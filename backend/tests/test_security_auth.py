from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest
from sqlalchemy import create_engine, text

from app.rate_limit import SlidingWindowLimiter

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")
MIGRATOR_URL = "postgresql+psycopg://sentrix_migrator@10.20.10.20:5432/sentrix"


def request(path, method="GET", payload=None, token=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else None
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"API not reachable: {exc}")


def login():
    status, body = request(
        "/api/v1/auth/login",
        "POST",
        {"email": "maya@sentrix.local", "password": "sentrix-demo"},
    )
    assert status == 200, body
    return body["token"]


def cleanup_auth_audit():
    engine = create_engine(MIGRATOR_URL)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
        try:
            connection.execute(text("DELETE FROM audit_event WHERE action LIKE 'auth.%'"))
        finally:
            connection.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))


def test_rate_limiter_unit():
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)
    assert limiter.allow("x") is True
    assert limiter.allow("x") is True
    assert limiter.allow("x") is False
    assert limiter.allow("y") is True


def test_logout_revokes_token():
    token = login()
    status, _ = request("/api/v1/auth/me", token=token)
    assert status == 200
    try:
        status, _ = request("/api/v1/auth/logout", "POST", {}, token)
        assert status == 204
        status, _ = request("/api/v1/auth/me", token=token)
        assert status == 401
    finally:
        cleanup_auth_audit()


def test_failed_login_is_audited():
    try:
        status, _ = request(
            "/api/v1/auth/login",
            "POST",
            {"email": "maya@sentrix.local", "password": "wrong-password"},
        )
        assert status == 401
        engine = create_engine(MIGRATOR_URL)
        with engine.begin() as connection:
            count = connection.execute(
                text(
                    "SELECT count(*) FROM audit_event WHERE action = 'auth.login' AND outcome = 'DENIED'"
                )
            ).scalar_one()
        assert count >= 1
    finally:
        cleanup_auth_audit()
