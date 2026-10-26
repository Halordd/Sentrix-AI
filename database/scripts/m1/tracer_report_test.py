import json
import urllib.request

BASE = "http://127.0.0.1:8008"


def post(path, payload):
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.load(response)


status, report = post(
    "/api/v1/reports",
    {"projectId": "project-atlas", "title": "Tracer report", "scanId": "scan-atlas"},
)
print("report", status, report)
status, published = post(f"/api/v1/reports/{report['id']}/publish", {})
print("publish", status, published)
print("CLEANUP", report["id"])
