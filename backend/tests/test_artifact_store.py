from __future__ import annotations

import hashlib

import pytest

from app.artifact_store import ArtifactStoreError, FilesystemArtifactStore


def test_put_get_delete_roundtrip(tmp_path):
    store = FilesystemArtifactStore(tmp_path)
    payload = b"independent evidence\n"
    key = store.put(payload)
    assert key == hashlib.sha256(payload).hexdigest()
    assert store.get(key) == payload
    store.delete(key)
    with pytest.raises(ArtifactStoreError):
        store.get(key)


def test_key_validation_rejects_traversal(tmp_path):
    store = FilesystemArtifactStore(tmp_path)
    with pytest.raises(ArtifactStoreError):
        store.get("../outside")
    with pytest.raises(ArtifactStoreError):
        store.get("A" * 64)


def test_oversized_artifact_rejected(tmp_path):
    store = FilesystemArtifactStore(tmp_path, max_bytes=4)
    with pytest.raises(ArtifactStoreError):
        store.put(b"12345")


def test_tampered_artifact_rejected(tmp_path):
    store = FilesystemArtifactStore(tmp_path)
    key = store.put(b"original")
    (tmp_path / key).write_bytes(b"tampered")
    with pytest.raises(ArtifactStoreError):
        store.get(key)
