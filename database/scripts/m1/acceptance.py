from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "http://10.20.10.10"
API_DIRECT = "http://127.0.0.1:8000"
AI = "http://10.20.10.30:8000"
TOKEN = ""


def request(path: str, base: str = API, method: str = "GET", payload: dict | None = None):
    headers = {"Accept": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = json.dumps(payload).encode() if payload is not None else None
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=8) as response:
        return response.status, response.read()


def main() -> int:
    global TOKEN
    failures: list[str] = []

    status, body = request(
        "/api/v1/auth/login",
        API_DIRECT,
        "POST",
        {"email": "maya@sentrix.local", "password": "sentrix-demo"},
    )
    print(f"POST /api/v1/auth/login -> {status}")
    if status != 200:
        print("ACCEPTANCE FAILED: login")
        return 1
    TOKEN = json.loads(body)["token"]

    for path in ("/health", "/health/db"):
        status, body = request(path, API_DIRECT)
        print(f"GET {path} -> {status}")
        if status != 200:
            failures.append(path)

    status, body = request("/api/v1/bootstrap")
    data = json.loads(body)
    expected = {
        "projects": 3,
        "targets": 4,
        "scans": 3,
        "findings": 3,
        "analyses": 1,
        "remediations": 1,
        "reports": 1,
        "audit": 2,
        "models": 2,
        "datasets": 1,
    }
    for key, count in expected.items():
        actual = len(data.get(key, []))
        print(f"bootstrap.{key} = {actual} (expected {count})")
        if actual != count:
            failures.append(f"bootstrap.{key}")

    status, body = request("/api/v1/scan-profiles")
    profiles = json.loads(body)
    print(f"scan_profiles = {len(profiles)} (expected 3)")
    if status != 200 or len(profiles) != 3:
        failures.append("scan_profiles")

    status, body = request("/")
    print(f"GET / -> {status}")
    if status != 200 or b"SENTRIX" not in body:
        failures.append("ui")

    try:
        status, _ = request("/health", AI)
        print(f"AI /health -> {status}")
        if status != 200:
            failures.append("ai")
    except Exception as exc:
        print(f"AI /health unavailable: {exc}")
        failures.append("ai")

    if failures:
        print("ACCEPTANCE FAILED: " + ", ".join(failures))
        return 1
    print("ACCEPTANCE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
