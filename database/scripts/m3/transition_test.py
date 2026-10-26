import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8011"
TOKEN = ""


def call(path, method="GET", payload=None):
    headers = {"Accept": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
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


status, login = call(
    "/api/v1/auth/login",
    "POST",
    {"email": "maya@sentrix.local", "password": "sentrix-demo"},
)
TOKEN = login["token"]
print("login", status)

status, body = call(
    "/api/v1/findings/finding-bola/transitions",
    "POST",
    {"to": "IN_PROGRESS"},
)
print("forbidden-confirmed-in-progress", status, body)

status, body = call(
    "/api/v1/findings/finding-bola/transitions",
    "POST",
    {"to": "RESOLVED", "reason": "should fail"},
)
print("forbidden-resolved", status, body)

status, body = call(
    "/api/v1/findings/finding-bola/transitions",
    "POST",
    {"to": "ACCEPTED_RISK", "reason": "Tracer transition for matrix test."},
)
print("allowed-confirmed-accepted-risk", status, body)
