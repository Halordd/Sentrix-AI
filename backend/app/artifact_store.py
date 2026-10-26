from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ArtifactStoreError(ValueError):
    pass


class FilesystemArtifactStore:
    """Content-addressed filesystem store guarded by SHA-256 keys."""

    def __init__(self, root: str | Path, max_bytes: int = 10 * 1024 * 1024) -> None:
        self.root = Path(root).resolve()
        self.max_bytes = max_bytes
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def _key(self, key: str) -> str:
        if not isinstance(key, str) or not SHA256_RE.fullmatch(key):
            raise ArtifactStoreError("artifact key must be a lowercase SHA-256 hex digest")
        return key

    def _path(self, key: str) -> Path:
        return self.root / key

    def put(self, data: bytes) -> str:
        if not isinstance(data, (bytes, bytearray)):
            raise ArtifactStoreError("artifact data must be bytes")
        if len(data) > self.max_bytes:
            raise ArtifactStoreError("artifact exceeds the configured size limit")
        payload = bytes(data)
        digest = hashlib.sha256(payload).hexdigest()
        path = self._path(digest)
        if path.exists():
            return digest
        fd, temporary = tempfile.mkstemp(prefix=".artifact-", dir=self.root)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return digest

    def get(self, key: str) -> bytes:
        digest = self._key(key)
        path = self._path(digest)
        if not path.is_file():
            raise ArtifactStoreError("artifact not found")
        payload = path.read_bytes()
        if len(payload) > self.max_bytes:
            raise ArtifactStoreError("artifact exceeds the configured size limit")
        actual = hashlib.sha256(payload).hexdigest()
        if actual != digest:
            raise ArtifactStoreError("artifact hash mismatch")
        return payload

    def delete(self, key: str) -> None:
        digest = self._key(key)
        self._path(digest).unlink(missing_ok=True)
