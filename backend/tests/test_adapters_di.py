from __future__ import annotations

import pytest

from app.adapters import (
    build_artifact_store,
    build_execution_backend,
    build_inference,
    build_scanner,
)
from app.demo_scanner import DemoScannerAdapter
from app.execution import SubprocessExecutionBackend
from app.mock_inference import MockInferenceAdapter


def test_default_adapters_are_swappable(monkeypatch):
    monkeypatch.delenv("SENTRIX_SCANNER_ADAPTER", raising=False)
    monkeypatch.delenv("SENTRIX_INFERENCE_ADAPTER", raising=False)
    monkeypatch.delenv("SENTRIX_EXECUTION_BACKEND", raising=False)

    assert isinstance(build_scanner(), DemoScannerAdapter)
    assert isinstance(build_inference(), MockInferenceAdapter)
    assert isinstance(build_execution_backend(), SubprocessExecutionBackend)


def test_unknown_adapter_is_rejected(monkeypatch):
    monkeypatch.setenv("SENTRIX_SCANNER_ADAPTER", "unknown")
    with pytest.raises(ValueError):
        build_scanner()


def test_artifact_store_uses_configured_root(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTRIX_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    store = build_artifact_store()
    key = store.put(b"demo")
    assert store.get(key) == b"demo"
