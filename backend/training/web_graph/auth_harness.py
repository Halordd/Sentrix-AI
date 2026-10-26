"""Authenticated BOLA/IDOR evidence collector.

Requires a human-supplied Juice Shop bearer token and object IDs. It sends
GET-only requests and records status/hash evidence. It does NOT auto-label:
every record is PENDING_HUMAN_REVIEW.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def probes(other_basket: str, other_user: str) -> list[tuple[str, str, str, str]]:
    return [
        ("BOLA basket access", f"/rest/basket/{other_basket}", "CWE-639", "HIGH"),
        ("BOLA user details access", f"/rest/user/authentication-details/{other_user}", "CWE-639", "HIGH"),
        ("BOLA address access", f"/api/Addresss/{other_user}", "CWE-639", "MEDIUM"),
        ("BOLA card access", f"/api/Cards/{other_user}", "CWE-639", "HIGH"),
        ("BOLA basket item access", f"/api/BasketItems/{other_basket}", "CWE-639", "HIGH"),
        ("BOLA complaint access", f"/api/Complaints/{other_user}", "CWE-639", "HIGH"),
        ("BOLA recycles access", f"/api/Recycles/{other_user}", "CWE-639", "MEDIUM"),
        ("BOLA delivery access", f"/api/Deliverys/{other_user}", "CWE-639", "MEDIUM"),
        ("BOLA security answer access", f"/api/SecurityAnswers/{other_user}", "CWE-200", "HIGH"),
        ("BOLA user listing access", "/api/Users", "CWE-200", "HIGH"),
        ("IDOR order history", "/rest/order-history", "CWE-639", "HIGH"),
        ("IDOR track order", "/rest/track-order/1", "CWE-639", "MEDIUM"),
        ("IDOR product basket", "/rest/basket/1", "CWE-639", "HIGH"),
        ("IDOR user details 1", "/rest/user/authentication-details/1", "CWE-639", "HIGH"),
        ("IDOR address 1", "/api/Addresss/1", "CWE-639", "MEDIUM"),
        ("IDOR card 1", "/api/Cards/1", "CWE-639", "HIGH"),
        ("IDOR complaint 1", "/api/Complaints/1", "CWE-639", "MEDIUM"),
        ("IDOR recycle 1", "/api/Recycles/1", "CWE-639", "LOW"),
        ("IDOR delivery 1", "/api/Deliverys/1", "CWE-639", "MEDIUM"),
        ("IDOR feedback 1", "/api/Feedbacks/1", "CWE-639", "LOW"),
    ]


def fetch(base: str, path: str, token: str) -> dict:
    request = urllib.request.Request(
        base.rstrip("/") + path,
        method="GET",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json", "User-Agent": "SENTRIX-BOLA-Harness/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read(65536)
            return {
                "status": response.status,
                "contentType": response.headers.get("Content-Type", ""),
                "bytes": len(body),
                "bodySha256": hashlib.sha256(body).hexdigest(),
            }
    except urllib.error.HTTPError as error:
        body = error.read(65536)
        return {
            "status": error.code,
            "contentType": error.headers.get("Content-Type", ""),
            "bytes": len(body),
            "bodySha256": hashlib.sha256(body).hexdigest(),
        }
    except Exception as exc:
        return {"status": 0, "error": str(exc), "contentType": "", "bytes": 0, "bodySha256": ""}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://10.20.20.20:3000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--other-basket", required=True)
    parser.add_argument("--other-user", required=True)
    parser.add_argument("--out", default="bola_corpus.json")
    args = parser.parse_args()
    records = []
    for index, (title, path, cwe, severity) in enumerate(
        probes(args.other_basket, args.other_user), start=1
    ):
        evidence = fetch(args.base, path, args.token)
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
                "observedAt": datetime.now(timezone.utc).isoformat(),
            }
        )
    Path(args.out).write_text(json.dumps({"base": args.base, "records": records}, indent=2))
    print(json.dumps({"output": args.out, "records": len(records), "review": "PENDING_HUMAN_REVIEW"}, indent=2))


if __name__ == "__main__":
    main()
