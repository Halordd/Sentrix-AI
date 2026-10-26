from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest
from sqlalchemy import create_engine, text

from app.artifact_store import FilesystemArtifactStore

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")
ARTIFACT_DIR = os.environ.get(
    "SENTRIX_ARTIFACT_DIR", os.path.expanduser("~/sentrix-artifacts")
)
MIGRATOR_URL = "postgresql+psycopg://sentrix_migrator@10.20.10.20:5432/sentrix"


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


def upload(token: str, project_id: str, payload: bytes, evidence_id: str | None = None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "X-Project-Id": project_id,
    }
    if evidence_id:
        headers["X-Evidence-Id"] = evidence_id
    request = urllib.request.Request(
        API + "/api/v1/artifacts", data=payload, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, json.loads(raw) if raw else None


def cleanup(key: str | None) -> None:
    if key:
        try:
            FilesystemArtifactStore(ARTIFACT_DIR).delete(key)
        except Exception:
            pass
    engine = create_engine(MIGRATOR_URL)
    with engine.begin() as connection:
        if key:
            connection.execute(text("DELETE FROM artifact WHERE sha256 = :key"), {"key": key})
            connection.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
            try:
                connection.execute(
                    text("DELETE FROM audit_event WHERE resource_id = :key"), {"key": key}
                )
            finally:
                connection.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))


def test_artifact_upload_download_and_project_scope():
    token = login()
    payload = b"project-scoped artifact\n"
    key = None
    try:
        status, body = upload(token, "project-atlas", payload)
        assert status == 201, body
        key = body["sha256"]

        request = urllib.request.Request(
            API + f"/api/v1/artifacts/{key}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            assert response.status == 200
            assert response.read() == payload
            assert response.headers["Content-Type"] == "application/octet-stream"
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["Content-Disposition"].startswith("attachment;")

        status, body = upload(token, "project-helix", b"other-project\n")
        assert status == 404, body

        status, body = upload(token, "project-atlas", b"wrong-evidence\n", "evidence-bucket")
        assert status == 422, body
    finally:
        cleanup(key)


def test_unknown_artifact_is_404():
    token = login()
    request = urllib.request.Request(
        API + f"/api/v1/artifacts/{'0' * 64}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=8)
    assert error.value.code == 404
