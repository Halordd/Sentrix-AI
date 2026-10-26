import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8015"


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
            body = response.read()
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        body = error.read()
        return error.code, json.loads(body) if body else None


def login(email, password):
    status, body = call(
        "/api/v1/auth/login",
        "POST",
        {"email": email, "password": password},
    )
    assert status == 200, body
    return body["token"]


maya = login("maya@sentrix.local", "sentrix-demo")
admin = login("admin@sentrix.local", "admin-demo")

status, members = call("/api/v1/projects/project-atlas/members", token=maya)
print("members-before", status, members)

status, member = call(
    "/api/v1/projects/project-atlas/members",
    "POST",
    {"userId": "user-jon", "role": "ANALYST"},
    maya,
)
print("add-member", status, member)

status, member = call(
    "/api/v1/projects/project-atlas/members/user-jon",
    "PATCH",
    {"role": "VIEWER"},
    maya,
)
print("change-member", status, member)

status, _ = call(
    "/api/v1/projects/project-atlas/members/user-jon",
    "DELETE",
    None,
    maya,
)
print("remove-member", status)

status, user = call(
    "/api/v1/users",
    "POST",
    {
        "displayName": "Tracer User",
        "email": "tracer-user@sentrix.local",
        "role": "ANALYST",
        "password": "tracer-password-123",
    },
    admin,
)
print("provision-user", status, user)

status, user = call(
    f"/api/v1/users/{user['id']}",
    "PATCH",
    {"displayName": "Tracer User Updated", "role": "VIEWER"},
    admin,
)
print("update-user", status, user)
print("CLEANUP_USER", user["id"])
