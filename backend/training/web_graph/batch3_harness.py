"""Batch 3: 40 GET-only candidates from the OWASP WebGoat lab.

Every record starts as PENDING_HUMAN_REVIEW. No exploit payloads, no auth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://10.20.20.20:8080"

HEADER_PROBES = [
    ("/WebGoat/login", "content-security-policy"),
    ("/WebGoat/registration", "content-security-policy"),
    ("/WebGoat/", "content-security-policy"),
    ("/WebGoat/login", "x-content-type-options"),
    ("/WebGoat/registration", "x-content-type-options"),
    ("/WebGoat/", "x-content-type-options"),
    ("/WebGoat/login", "x-frame-options"),
    ("/WebGoat/registration", "x-frame-options"),
    ("/WebGoat/", "x-frame-options"),
    ("/WebGoat/login", "referrer-policy"),
    ("/WebGoat/registration", "referrer-policy"),
    ("/WebGoat/", "referrer-policy"),
    ("/WebGoat/login", "strict-transport-security"),
    ("/WebGoat/registration", "strict-transport-security"),
    ("/WebGoat/", "strict-transport-security"),
    ("/WebGoat/login", "permissions-policy"),
    ("/WebGoat/registration", "permissions-policy"),
    ("/WebGoat/", "permissions-policy"),
    ("/WebGoat/login", "cache-control"),
    ("/WebGoat/registration", "cache-control"),
]

SENSITIVE_PROBES = [
    ("Actuator root", "/WebGoat/actuator", "CWE-200", "MEDIUM"),
    ("Actuator health", "/WebGoat/actuator/health", "CWE-200", "LOW"),
    ("Actuator info", "/WebGoat/actuator/info", "CWE-200", "LOW"),
    ("Actuator env", "/WebGoat/actuator/env", "CWE-200", "HIGH"),
    ("Actuator mappings", "/WebGoat/actuator/mappings", "CWE-200", "MEDIUM"),
    ("Actuator beans", "/WebGoat/actuator/beans", "CWE-200", "MEDIUM"),
    ("Actuator metrics", "/WebGoat/actuator/metrics", "CWE-200", "LOW"),
    ("Actuator loggers", "/WebGoat/actuator/loggers", "CWE-200", "MEDIUM"),
    ("Actuator configprops", "/WebGoat/actuator/configprops", "CWE-200", "HIGH"),
    ("Actuator threaddump", "/WebGoat/actuator/threaddump", "CWE-200", "MEDIUM"),
    ("Actuator heapdump", "/WebGoat/actuator/heapdump", "CWE-200", "HIGH"),
    ("Actuator prometheus", "/WebGoat/actuator/prometheus", "CWE-200", "MEDIUM"),
    ("Robots file", "/WebGoat/robots.txt", "CWE-200", "LOW"),
    ("Git metadata", "/WebGoat/.git/config", "CWE-538", "HIGH"),
    ("Registration page", "/WebGoat/registration", "CWE-200", "LOW"),
    ("Login error page", "/WebGoat/login?error", "CWE-200", "LOW"),
    ("Static JS bundle", "/WebGoat/js/main.js", "CWE-540", "LOW"),
    ("Static CSS bundle", "/WebGoat/css/main.css", "CWE-540", "LOW"),
    ("Swagger UI check", "/WebGoat/swagger-ui/index.html", "CWE-200", "MEDIUM"),
    ("H2 console check", "/WebGoat/h2-console", "CWE-200", "MEDIUM"),
]


def fetch(path: str) -> dict:
    request = urllib.request.Request(
        BASE + path,
        method="GET",
        headers={"User-Agent": "SENTRIX-WebGoat-Harness/1.0", "Accept": "*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read(65536)
            return {
                "status": response.status,
                "contentType": response.headers.get("Content-Type", ""),
                "bytes": len(body),
                "bodySha256": hashlib.sha256(body).hexdigest(),
                "headers": {key.lower(): value for key, value in response.headers.items()},
            }
    except urllib.error.HTTPError as error:
        body = error.read(65536)
        return {
            "status": error.code,
            "contentType": error.headers.get("Content-Type", ""),
            "bytes": len(body),
            "bodySha256": hashlib.sha256(body).hexdigest(),
            "headers": {key.lower(): value for key, value in error.headers.items()},
        }
    except Exception as exc:
        return {"status": 0, "error": str(exc), "contentType": "", "bytes": 0, "bodySha256": "", "headers": {}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="web_corpus_batch3.json")
    args = parser.parse_args()
    records = []
    for index, (path, header) in enumerate(HEADER_PROBES, start=1):
        observation = fetch(path)
        missing = header not in observation["headers"]
        records.append(
            {
                "id": f"b3-head-{index:02d}",
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
    for index, (title, path, cwe, severity) in enumerate(SENSITIVE_PROBES, start=1):
        observation = fetch(path)
        records.append(
            {
                "id": f"b3-path-{index:02d}",
                "title": title,
                "severity": severity,
                "cwe": cwe,
                "source": "DAST",
                "location": {"kind": "url", "value": path, "line": None},
                "verified": False,
                "label": None,
                "reviewStatus": "PENDING_HUMAN_REVIEW",
                "evidence": {key: observation[key] for key in ("status", "contentType", "bytes", "bodySha256")},
                "observedAt": datetime.now(timezone.utc).isoformat(),
            }
        )
    Path(args.out).write_text(json.dumps({"base": BASE, "records": records}, indent=2))
    print(
        json.dumps(
            {
                "output": args.out,
                "records": len(records),
                "headerCandidates": sum(1 for record in records if record.get("ruleHint") == 1),
                "path200": sum(
                    1
                    for record in records
                    if record["id"].startswith("b3-path-") and record["evidence"]["status"] == 200
                ),
                "review": "PENDING_HUMAN_REVIEW",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
