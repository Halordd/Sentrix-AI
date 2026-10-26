import json
import urllib.request

BASE = "http://127.0.0.1:8007"


def post(path, payload):
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.load(response)


status, task = post(
    "/api/v1/findings/finding-bucket/remediations",
    {"assignee": "Maya Chen", "dueDate": "2026-10-25", "notes": "Tracer remediation"},
)
print("remediation", status, task)
status, verified = post(
    f"/api/v1/remediations/{task['id']}/verify",
    {"outcome": "VERIFIED", "method": "MANUAL_REVIEW", "notes": "Tracer verification"},
)
print("verify", status, verified)
print("CLEANUP", task["id"])
