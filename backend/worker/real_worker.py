from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

API = "http://10.20.10.10/api/v1"
POLL_SECONDS = 8
EMAIL = os.getenv("SENTRIX_EMAIL", "maya@sentrix.local")
PASSWORD = os.getenv("SENTRIX_PASSWORD", "sentrix-demo")
TOKEN = ""


def _request(path: str, method: str, payload: dict | None = None) -> dict | None:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(
        API + path, data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def login() -> None:
    global TOKEN
    result = _request(
        "/auth/login", "POST", {"email": EMAIL, "password": PASSWORD}
    )
    TOKEN = result["token"]
    print(f"authenticated as {result['user']['email']}", flush=True)


def call(path: str, method: str, payload: dict | None = None) -> dict | None:
    global TOKEN
    try:
        return _request(path, method, payload)
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
        TOKEN = ""
        login()
        return _request(path, method, payload)


def main() -> None:
    print(f"sentrix-worker polling {API} every {POLL_SECONDS}s", flush=True)
    login()
    while True:
        try:
            claim = call("/worker/claims", "POST", {})
            if claim is None:
                print("idle", flush=True)
            else:
                job = claim["job"]
                run_id = claim["runId"]
                print(f"claimed {job['id']} run={run_id}", flush=True)
                call(f"/worker/claims/{run_id}/heartbeat", "POST", {})
                result = call(f"/scans/{job['id']}/run", "POST", {})
                print(
                    f"completed {job['id']} finding={result['finding']['id']}",
                    flush=True,
                )
        except Exception as exc:  # keep the worker alive for later polls
            print(f"poll failed: {exc}", flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
