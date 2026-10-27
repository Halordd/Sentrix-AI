from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")
ADMIN = ("admin@sentrix.local", "admin-demo")
ANALYST = ("maya@sentrix.local", "sentrix-demo")


def login(credentials: tuple[str, str]) -> str:
    request = urllib.request.Request(
        API + "/api/v1/auth/login",
        data=json.dumps({"email": credentials[0], "password": credentials[1]}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read())["token"]
    except (OSError, urllib.error.URLError) as exc:
        pytest.skip(f"API not reachable: {exc}")


def get(path: str, token: str) -> tuple[int, dict]:
    request = urllib.request.Request(
        API + path, headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, {}


def test_corpus_routes_are_admin_only():
    analyst = login(ANALYST)
    status, _ = get("/api/v1/corpus/projects", analyst)
    if status == 404:
        pytest.skip("corpus routes not deployed yet")
    assert status == 403


def test_corpus_admin_summary_is_pilot_labelled():
    admin = login(ADMIN)
    status, body = get("/api/v1/corpus/projects", admin)
    if status == 404:
        pytest.skip("corpus routes not deployed yet")
    assert status == 200
    assert body["pilot"] is True
    assert body["scoreLabel"] == "pilot-uncalibrated"
    assert body["project"]["id"] == "project-corpus-pilot"
    assert sum(target["findings"] for target in body["targets"]) == 141


def test_corpus_invalid_limit_returns_400():
    admin = login(ADMIN)
    status, _ = get("/api/v1/corpus/findings?limit=abc", admin)
    if status == 404:
        pytest.skip("corpus routes not deployed yet")
    assert status == 400
