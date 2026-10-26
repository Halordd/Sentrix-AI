import json
import urllib.request

BASE = "http://127.0.0.1:8004"


def post(path, payload):
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.load(response)


status, target = post(
    "/api/v1/targets",
    {
        "projectId": "project-atlas",
        "name": "Tracer Target",
        "type": "API",
        "scope": "https://tracer.local/*",
        "authorizationConfirmed": True,
    },
)
print("target", status, target)
status, scan = post(
    "/api/v1/scans",
    {
        "targetId": target["id"],
        "name": "Tracer Scan",
        "profile": "API authorization",
    },
)
print("scan", status, scan)
status, result = post(f"/api/v1/scans/{scan['id']}/run", {})
print("run", status, result)
print("CLEANUP", target["id"], scan["id"], result["finding"]["id"])
