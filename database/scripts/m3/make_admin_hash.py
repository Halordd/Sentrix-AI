import base64
import hashlib

salt = b"sentrix-admin-salt-2026"
digest = hashlib.pbkdf2_hmac("sha256", b"admin-demo", salt, 210000)
print(
    "pbkdf2_sha256$210000$"
    + base64.b64encode(salt).decode()
    + "$"
    + base64.b64encode(digest).decode()
)
