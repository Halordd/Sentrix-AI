"""Batch 2: 41 lab records (21 header + 20 BOLA/IDOR probes).

All records start as PENDING_HUMAN_REVIEW. The header probes are GET-only.
The BOLA probes create two disposable local accounts (POST /api/Users and
/api/auth/login) and then issue GET-only cross-user requests; this is a
setup write, not target exploitation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://10.20.20.20:3000"

HEADER_PROBES = [
    ("/login.html", "x-content-type-options"),
    ("/register.html", "x-content-type-options"),
    ("/forgot-password.html", "x-content-type-options"),
    ("/search", "content-security-policy"),
    ("/basket", "content-security-policy"),
    ("/order-history", "content-security-policy"),
    ("/admin", "content-security-policy"),
    ("/accounting", "content-security-policy"),
    ("/api/Products", "x-content-type-options"),
    ("/api/Feedbacks", "x-content-type-options"),
    ("/rest/user/login", "x-content-type-options"),
    ("/rest/products/search", "x-content-type-options"),
    ("/assets/public/images/", "x-content-type-options"),
    ("/robots.txt", "content-security-policy"),
    ("/security.txt", "content-security-policy"),
    ("/ftp", "x-frame-options"),
    ("/metrics", "x-frame-options"),
    ("/api/Users", "x-content-type-options"),
    ("/rest/memories", "content-security-policy"),
    ("/api/Challenges", "content-security-policy"),
    ("/login.html", "content-security-policy"),
]

BOLA_PROBES = [
    ("Cross-user basket by id", "/rest/basket/{other_basket}", "CWE-639", "HIGH"),
    ("Cross-user user details", "/rest/user/authentication-details/{other_user}", "CWE-639", "HIGH"),
    ("Cross-user address by id", "/api/Addresss/{other_user}", "CWE-639", "MEDIUM"),
    ("Cross-user card by id", "/api/Cards/{other_user}", "CWE-639", "HIGH"),
    ("Cross-user basket items", "/api/BasketItems/{other_basket}", "CWE-639", "HIGH"),
    ("Cross-user complaints", "/api/Complaints/{other_user}", "CWE-639", "HIGH"),
    ("Cross-user recycles", "/api/Recycles/{other_user}", "CWE-639", "MEDIUM"),
    ("Cross-user deliveries", "/api/Deliverys/{other_user}", "CWE-639", "MEDIUM"),
    ("Cross-user security answers", "/api/SecurityAnswers/{other_user}", "CWE-200", "HIGH"),
    ("Cross-user order history", "/rest/order-history?userId={other_user}", "CWE-639", "HIGH"),
    ("Cross-user track order", "/rest/track-order/{other_user}", "CWE-639", "MEDIUM"),
    ("BOLA basket id 1", "/rest/basket/1", "CWE-639", "HIGH"),
    ("BOLA user details id 1", "/rest/user/authentication-details/1", "CWE-639", "HIGH"),
    ("BOLA address id 1", "/api/Addresss/1", "CWE-639", "MEDIUM"),
    ("BOLA card id 1", "/api/Cards/1", "CWE-639", "HIGH"),
    ("BOLA complaint id 1", "/api/Complaints/1", "CWE-639", "MEDIUM"),
    ("BOLA recycle id 1", "/api/Recycles/1", "CWE-639", "LOW"),
    ("BOLA delivery id 1", "/api/Deliverys/1", "CWE-639", "MEDIUM"),
    ("BOLA feedback id 1", "/api/Feedbacks/1", "CWE-639", "LOW"),
    ("BOLA basket items query", "/api/BasketItems?basketId={other_basket}", "CWE-639", "HIGH"),
]


def fetch(path: str, token: str | None = None) -> dict:
    headers = {"Accept": "*/*", "User-Agent": "SENTRIX-Batch2/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/json"
    request = urllib.request.Request(BASE + path, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read(65536)
            return {
                "status": response.status,
                "contentType": response.headers.get("Content-Type", ""),
                "bytes": len(body),
                "bodySha256": hashlib.sha256(body).hexdigest(),
                "headers": {k.lower(): v for k, v in response.headers.items()},
            }
    except urllib.error.HTTPError as error:
        body = error.read(65536)
        return {
            "status": error.code,
            "contentType": error.headers.get("Content-Type", ""),
            "bytes": len(body),
            "bodySha256": hashlib.sha256(body).hexdigest(),
            "headers": {k.lower(): v for k, v in error.headers.items()},
        }
    except Exception as exc:
        return {"status": 0, "error": str(exc), "contentType": "", "bytes": 0, "bodySha256": "", "headers": {}}


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
    email = f"sentrix.b2.{tag}.{uuid.uuid4().hex[:10]}@example.com"
    password = os.environ.get("SENTRIX_LAB_PASSWORD", "")
    if not password:
        raise SystemExit("set SENTRIX_LAB_PASSWORD for disposable lab accounts")
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
    return {"id": user_id, "bid": auth["bid"], "token": auth["token"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="web_corpus_batch2.json")
    args = parser.parse_args()
    records = []

    for index, (path, header) in enumerate(HEADER_PROBES, start=1):
        observation = fetch(path)
        missing = header not in observation["headers"]
        records.append(
            {
                "id": f"b2-head-{index:02d}",
                "title": f"Missing {header} on {path}",
                "severity": "LOW",
                "cwe": "CWE-693",
                "source": "DAST",
                "location": {"kind": "url", "value": path, "line": None},
                "verified": False,
                "label": None,
                "reviewStatus": "PENDING_HUMAN_REVIEW",
                "ruleHint": 1 if missing else 0,
                "labelReason": f"{header} {'missing' if missing else 'present'}",
                "evidence": {key: observation[key] for key in ("status", "contentType", "bytes", "bodySha256")},
                "observedAt": datetime.now(timezone.utc).isoformat(),
            }
        )

    a = create_account("a")
    b = create_account("b")
    for index, (title, template, cwe, severity) in enumerate(BOLA_PROBES, start=1):
        path = template.format(other_basket=b["bid"], other_user=b["id"])
        observation = fetch(path, a["token"])
        records.append(
            {
                "id": f"b2-bola-{index:02d}",
                "title": title,
                "severity": severity,
                "cwe": cwe,
                "source": "DAST",
                "location": {"kind": "url", "value": path, "line": None},
                "verified": False,
                "label": None,
                "reviewStatus": "PENDING_HUMAN_REVIEW",
                "evidence": {key: observation[key] for key in ("status", "contentType", "bytes", "bodySha256")},
                "accounts": {"ownBasket": a["bid"], "otherBasket": b["bid"], "otherUser": b["id"]},
                "observedAt": datetime.now(timezone.utc).isoformat(),
            }
        )

    Path(args.out).write_text(json.dumps({"base": BASE, "records": records}, indent=2))
    print(
        json.dumps(
            {
                "output": args.out,
                "records": len(records),
                "headerCandidates": sum(1 for r in records if r.get("ruleHint") == 1),
                "bola200": sum(1 for r in records if r["id"].startswith("b2-bola") and r["evidence"]["status"] == 200),
                "review": "PENDING_HUMAN_REVIEW",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
