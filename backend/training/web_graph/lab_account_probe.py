import json
import os
import urllib.request
import uuid

BASE = "http://10.20.20.20:3000"
email = f"sentrix.lab.{uuid.uuid4().hex[:8]}@example.com"
password = os.environ.get("SENTRIX_LAB_PASSWORD", "")
if not password:
    raise SystemExit("set SENTRIX_LAB_PASSWORD")


def post(path, payload):
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


print("register", post("/api/Users", {
    "email": email,
    "password": password,
    "securityQuestion": {"id": 1},
    "securityAnswer": "sentrix",
}))
print("login", post("/rest/user/login", {"email": email, "password": password}))
