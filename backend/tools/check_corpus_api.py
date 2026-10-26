import json
import os
import urllib.request

BASE = "http://127.0.0.1:8045/api/v1"
EMAIL = os.environ.get("SENTRIX_ADMIN_EMAIL", "")
PASSWORD = os.environ.get("SENTRIX_ADMIN_PASSWORD", "")
if not EMAIL or not PASSWORD:
    raise SystemExit("set SENTRIX_ADMIN_EMAIL and SENTRIX_ADMIN_PASSWORD")


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read())


status, login = call(
    "POST",
    "/auth/login",
    body={"email": EMAIL, "password": PASSWORD},
)
token = login["token"]
projects = call("GET", "/corpus/projects", token)[1]
candidates = call("GET", "/corpus/candidates?limit=3", token)[1]
findings = call("GET", "/corpus/findings?targetId=target-webgoat&limit=3", token)[1]
print(
    json.dumps(
        {
            "loginStatus": status,
            "project": projects["project"]["id"],
            "targets": projects["targets"],
            "pilot": projects["pilot"],
            "scoreLabel": projects["scoreLabel"],
            "topCandidates": [
                {"sourceId": item["sourceId"], "score": item["score"], "verified": item["verified"]}
                for item in candidates["candidates"]
            ],
            "webgoatFindings": [
                {"sourceId": item["sourceId"], "score": item["score"], "verified": item["verified"]}
                for item in findings["findings"]
            ],
        },
        indent=2,
    )
)
