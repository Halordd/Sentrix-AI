"""Create two disposable Juice Shop accounts and collect BOLA/IDOR evidence.

Local lab only. GET-only evidence collection; no payloads. Tokens are not
written to disk. Every record is PENDING_HUMAN_REVIEW.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from auth_harness import fetch, probes

BASE = "http://10.20.20.20:3000"


def post(path: str, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, {"detail": error.read().decode()}


def create_account(tag: str) -> dict:
    email = f"sentrix.{tag}.{uuid.uuid4().hex[:10]}@example.com"
    password = "SentrixLab123!"
    status, body = post(
        "/api/Users",
        {
            "email": email,
            "password": password,
            "securityQuestion": {"id": 1},
            "securityAnswer": "sentrix",
        },
    )
    if status != 201:
        raise RuntimeError(f"register {tag} failed: {status} {body}")
    user_id = body["data"]["id"]
    status, body = post("/rest/user/login", {"email": email, "password": password})
    if status != 200:
        raise RuntimeError(f"login {tag} failed: {status} {body}")
    auth = body["authentication"]
    return {
        "id": user_id,
        "user": body["authentication"].get("umail"),
        "token": auth["token"],
        "bid": auth["bid"],
    }


def main() -> None:
    a = create_account("a")
    b = create_account("b")
    records = []
    for index, (title, path, cwe, severity) in enumerate(probes(str(b["bid"]), str(b["id"])), start=1):
        evidence = fetch(BASE, path, a["token"])
        records.append(
            {
                "id": f"bola-{index:02d}",
                "title": title,
                "severity": severity,
                "cwe": cwe,
                "source": "DAST",
                "location": {"kind": "url", "value": path, "line": None},
                "verified": False,
                "label": None,
                "reviewStatus": "PENDING_HUMAN_REVIEW",
                "evidence": evidence,
                "accounts": {"ownBasket": a["bid"], "otherBasket": b["bid"], "otherUser": b["id"]},
            }
        )
    out = Path("bola_corpus.json")
    out.write_text(json.dumps({"base": BASE, "records": records}, indent=2))
    print(json.dumps({"output": str(out), "records": len(records), "review": "PENDING_HUMAN_REVIEW"}, indent=2))


if __name__ == "__main__":
    main()
