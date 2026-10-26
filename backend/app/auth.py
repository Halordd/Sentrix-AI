from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

ITERATIONS = 210_000
SECRET = os.getenv("SENTRIX_SECRET_KEY", "sentrix-local-dev-secret-change-me")
TOKEN_TTL_SECONDS = 8 * 60 * 60
REVOKED_TOKENS: set[str] = set()


def _shared_auth() -> bool:
    return os.getenv("SENTRIX_SHARED_AUTH", "0") == "1"


def _fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def revoke_token(token: str) -> None:
    fingerprint = _fingerprint(token)
    REVOKED_TOKENS.add(fingerprint)
    if not _shared_auth():
        return
    try:
        from .db import get_engine
        from sqlalchemy import text

        with get_engine().begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO revoked_token (fingerprint, expires_at)
                    VALUES (:fingerprint, now() + interval '8 hours')
                    ON CONFLICT (fingerprint) DO NOTHING
                    """
                ),
                {"fingerprint": fingerprint},
            )
    except Exception:
        # Keep the local denylist if the shared store is unavailable.
        pass


def is_token_revoked(token: str) -> bool:
    fingerprint = _fingerprint(token)
    if _shared_auth():
        try:
            from .db import get_engine
            from sqlalchemy import text

            with get_engine().connect() as connection:
                row = connection.execute(
                    text(
                        """
                        SELECT 1 FROM revoked_token
                        WHERE fingerprint = :fingerprint AND expires_at > now()
                        """
                    ),
                    {"fingerprint": fingerprint},
                ).first()
            if row is not None:
                return True
        except Exception:
            pass
    return fingerprint in REVOKED_TOKENS


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return (
        f"pbkdf2_sha256${ITERATIONS}$"
        f"{base64.b64encode(salt).decode()}$"
        f"{base64.b64encode(digest).decode()}"
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt, int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def issue_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        "nonce": secrets.token_hex(8),
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def verify_token(token: str) -> dict | None:
    try:
        body, signature = token.split(".")
        expected = hmac.new(
            SECRET.encode(), body.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            return None
        payload = json.loads(_unb64(body))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
