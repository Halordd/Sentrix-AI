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


def call(path: str, method="GET", payload=None, token=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else None
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"API not reachable: {exc}")


def login(email: str, password: str) -> str:
    status, body = call(
        "/api/v1/auth/login", "POST", {"email": email, "password": password}
    )
    assert status == 200, body
    return body["token"]


def cleanup(user_id: str | None) -> None:
    engine = create_engine(MIGRATOR_URL)
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM project_member WHERE project_id = 'project-atlas' AND user_id = 'user-jon'"
            )
        )
        if user_id:
            connection.execute(text("DELETE FROM app_user WHERE id = :id"), {"id": user_id})
        connection.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
        try:
            connection.execute(
                text(
                    """
                    DELETE FROM audit_event
                    WHERE action LIKE 'membership.%'
                       OR action IN ('user.created', 'user.updated')
                    """
                )
            )
        finally:
            connection.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))


def test_membership_and_provisioning():
    maya = login("maya@sentrix.local", "sentrix-demo")
    admin = login("admin@sentrix.local", "admin-demo")
    user_id = None
    try:
        status, member = call(
            "/api/v1/projects/project-atlas/members",
            "POST",
            {"userId": "user-jon", "role": "ANALYST"},
            maya,
        )
        assert status == 201, member

        status, body = call(
            "/api/v1/projects/project-atlas/members",
            "POST",
            {"userId": "user-jon", "role": "ANALYST"},
            maya,
        )
        assert status == 409, body

        status, body = call(
            "/api/v1/projects/project-atlas/members/user-jon",
            "PATCH",
            {"role": "VIEWER"},
            maya,
        )
        assert status == 200, body

        status, body = call(
            "/api/v1/projects/project-atlas/members/user-maya",
            "PATCH",
            {"role": "VIEWER"},
            maya,
        )
        assert status == 409, body

        status, _ = call(
            "/api/v1/projects/project-atlas/members/user-jon",
            "DELETE",
            None,
            maya,
        )
        assert status == 204

        suffix = uuid4().hex[:8]
        status, user = call(
            "/api/v1/users",
            "POST",
            {
                "displayName": f"Tracer {suffix}",
                "email": f"tracer-{suffix}@sentrix.local",
                "role": "ANALYST",
                "password": "tracer-password-123",
            },
            admin,
        )
        assert status == 201, user
        user_id = user["id"]

        status, updated = call(
            f"/api/v1/users/{user_id}",
            "PATCH",
            {"displayName": "Tracer Updated", "role": "VIEWER"},
            admin,
        )
        assert status == 200, updated
        assert updated["role"] == "VIEWER"
    finally:
        cleanup(user_id)
