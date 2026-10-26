"""Non-destructive web/API observation harness for the SENTRIX lab.

GET-only. It records 20 candidate findings with status/header evidence and a
deterministic verified/false-positive label. It never sends exploit payloads,
never authenticates, and never modifies the target.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROBES = [
    # (title, path, cwe, severity, check)
    ("Missing X-Content-Type-Options header on /", "/", "CWE-693", "LOW", "missing_header"),
    ("Missing Content-Security-Policy header on /", "/", "CWE-693", "LOW", "missing_header"),
    ("Missing X-Frame-Options header on /", "/", "CWE-693", "LOW", "missing_header"),
    ("Missing Referrer-Policy header on /", "/", "CWE-693", "LOW", "missing_header"),
    ("Server banner disclosure on /", "/", "CWE-200", "LOW", "server_banner"),
    ("Unauthenticated API product listing", "/api/Products", "CWE-306", "LOW", "public_api"),
    ("Unauthenticated feedback listing", "/api/Feedbacks", "CWE-306", "LOW", "public_api"),
    ("Unauthenticated challenge listing", "/api/Challenges", "CWE-306", "LOW", "public_api"),
    ("Public application configuration", "/rest/admin/application-configuration", "CWE-200", "MEDIUM", "sensitive_path"),
    ("Public security questions list", "/api/SecurityQuestions", "CWE-200", "MEDIUM", "sensitive_path"),
    ("Robots file discloses paths", "/robots.txt", "CWE-200", "LOW", "robots"),
    ("Security contact file absent", "/.well-known/security.txt", "CWE-1059", "INFO", "absent"),
    ("Source map exposure check", "/main.js.map", "CWE-540", "MEDIUM", "sensitive_path"),
    ("Git metadata exposure check", "/.git/config", "CWE-538", "HIGH", "sensitive_path"),
    ("Metrics endpoint exposure check", "/metrics", "CWE-200", "MEDIUM", "sensitive_path"),
    ("FTP directory exposure check", "/ftp", "CWE-548", "MEDIUM", "sensitive_path"),
    ("User authentication details exposure check", "/rest/user/authentication-details/1", "CWE-639", "HIGH", "sensitive_path"),
    ("Basket access without session", "/rest/basket/1", "CWE-639", "HIGH", "sensitive_path"),
    ("Address listing without session", "/api/Addresss", "CWE-639", "MEDIUM", "sensitive_path"),
    ("Quantity listing without session", "/api/Quantitys", "CWE-306", "LOW", "public_api"),
    ("Single product lookup", "/api/Products/1", "CWE-306", "LOW", "public_api"),
    ("Single feedback lookup", "/api/Feedbacks/1", "CWE-306", "LOW", "public_api"),
    ("Single challenge lookup", "/api/Challenges/1", "CWE-306", "LOW", "public_api"),
    ("Product detail endpoint", "/rest/product/1", "CWE-306", "LOW", "public_api"),
    ("Whoami endpoint without auth", "/rest/user/whoami", "CWE-306", "LOW", "sensitive_path"),
    ("Save login IP endpoint", "/rest/saveLoginIp", "CWE-306", "LOW", "sensitive_path"),
    ("Track order lookup", "/rest/track-order/1", "CWE-639", "MEDIUM", "sensitive_path"),
    ("Order history without session", "/rest/order-history", "CWE-639", "HIGH", "sensitive_path"),
    ("Continue code endpoint", "/rest/continue-code", "CWE-306", "LOW", "public_api"),
    ("Continue code apply endpoint", "/rest/continue-code/apply", "CWE-306", "LOW", "sensitive_path"),
    ("Memories listing", "/rest/memories", "CWE-200", "MEDIUM", "sensitive_path"),
    ("Recycle listing", "/api/Recycles", "CWE-306", "LOW", "public_api"),
    ("Delivery listing", "/api/Deliverys", "CWE-306", "LOW", "sensitive_path"),
    ("Card listing", "/api/Cards", "CWE-639", "HIGH", "sensitive_path"),
    ("Basket item listing", "/api/BasketItems", "CWE-639", "HIGH", "sensitive_path"),
    ("Complaint listing", "/api/Complaints", "CWE-639", "HIGH", "sensitive_path"),
    ("Security answer listing", "/api/SecurityAnswers", "CWE-200", "HIGH", "sensitive_path"),
    ("User listing", "/api/Users", "CWE-200", "HIGH", "sensitive_path"),
    ("Product search endpoint", "/api/Products/search?q=", "CWE-306", "LOW", "public_api"),
    ("Product query endpoint", "/api/Products?q=", "CWE-306", "LOW", "public_api"),
]

SECURITY_HEADERS = {
    "x-content-type-options",
    "content-security-policy",
    "x-frame-options",
    "referrer-policy",
}


def fetch(base: str, path: str) -> dict:
    request = urllib.request.Request(
        base.rstrip("/") + path,
        method="GET",
        headers={"User-Agent": "SENTRIX-Lab-Harness/1.0", "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read(65536)
            return {
                "status": response.status,
                "headers": {key.lower(): value for key, value in response.headers.items()},
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "content_type": response.headers.get("Content-Type", ""),
            }
    except urllib.error.HTTPError as error:
        body = error.read(65536)
        return {
            "status": error.code,
            "headers": {key.lower(): value for key, value in error.headers.items()},
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "bytes": len(body),
            "content_type": error.headers.get("Content-Type", ""),
        }
    except Exception as exc:
        return {"status": 0, "error": str(exc), "headers": {}, "body_sha256": "", "bytes": 0, "content_type": ""}


def classify(check: str, observation: dict) -> tuple[int, str]:
    if check == "missing_header":
        return 1, "header_baseline"
    if check == "server_banner":
        return (1 if observation["headers"].get("server") else 0), "server_header"
    if check == "public_api":
        return 0, "public_by_design"
    if check == "absent":
        return (1 if observation["status"] == 404 else 0), "absence_only"
    if check == "robots":
        return (1 if observation["status"] == 200 else 0), "robots_public"
    if check == "sensitive_path":
        # SPA fallback often returns HTML 200; only JSON/non-HTML 200 counts.
        if observation["status"] == 200 and "json" in observation.get("content_type", "").lower():
            return 1, "confirmed_non_html_200"
        return 0, "not_confirmed"
    return 0, "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://10.20.20.20:3000")
    parser.add_argument("--out", default="web_corpus.json")
    args = parser.parse_args()
    records = []
    for index, (title, path, cwe, severity, check) in enumerate(PROBES, start=1):
        observation = fetch(args.base, path)
        if check == "missing_header":
            header = {
                1: "x-content-type-options",
                2: "content-security-policy",
                3: "x-frame-options",
                4: "referrer-policy",
            }[index]
            verified = 0 if header in observation["headers"] else 1
            reason = f"{header} present" if not verified else f"{header} missing"
        else:
            verified, reason = classify(check, observation)
        records.append(
            {
                "id": f"corpus-{index:02d}",
                "title": title,
                "severity": severity,
                "cwe": cwe,
                "source": "DAST",
                "location": {"kind": "url", "value": path, "line": None},
                "verified": bool(verified),
                "reviewStatus": "RULE_ONLY",
                "label": verified,
                "labelReason": reason,
                "evidence": {
                    "status": observation["status"],
                    "contentType": observation["content_type"],
                    "bytes": observation["bytes"],
                    "bodySha256": observation["body_sha256"],
                },
                "observedAt": datetime.now(timezone.utc).isoformat(),
            }
        )
    out = Path(args.out)
    out.write_text(json.dumps({"base": args.base, "records": records}, indent=2))
    print(
        json.dumps(
            {
                "output": str(out),
                "records": len(records),
                "verified": sum(item["label"] for item in records),
                "false_positive_candidates": sum(1 for item in records if not item["label"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
