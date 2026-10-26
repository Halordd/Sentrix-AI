import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8010"


def call(path, method="GET", payload=None, token=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


status, body = call(
    "/api/v1/auth/login",
    "POST",
    {"email": "maya@sentrix.local", "password": "sentrix-demo"},
)
print("login", status, body.get("user"))
token = body["token"]

status, body = call("/api/v1/bootstrap")
print("bootstrap-no-token", status, body)
status, body = call("/api/v1/bootstrap", token=token)
print("bootstrap-token", status, len(body.get("projects", [])))
status, body = call("/api/v1/auth/me", token=token)
print("me", status, body)
