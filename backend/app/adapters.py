from __future__ import annotations

import os
from pathlib import Path

from .artifact_store import FilesystemArtifactStore
from .demo_scanner import DemoScannerAdapter
from .execution import SubprocessExecutionBackend
from .mock_inference import MockInferenceAdapter
from .ports import (
    ArtifactStorePort,
    ExecutionBackend,
    InferencePort,
    ScannerPort,
)


def _choice(name: str) -> str:
    return os.getenv(name, "").strip().lower()


def build_scanner() -> ScannerPort:
    choice = _choice("SENTRIX_SCANNER_ADAPTER") or "demo"
    if choice == "demo":
        return DemoScannerAdapter()
    raise ValueError(f"unknown scanner adapter: {choice}")


def build_inference() -> InferencePort:
    choice = _choice("SENTRIX_INFERENCE_ADAPTER") or "mock"
    if choice == "mock":
        return MockInferenceAdapter()
    raise ValueError(f"unknown inference adapter: {choice}")


def build_execution_backend() -> ExecutionBackend:
    choice = _choice("SENTRIX_EXECUTION_BACKEND") or "subprocess"
    if choice == "subprocess":
        return SubprocessExecutionBackend()
    raise ValueError(f"unknown execution backend: {choice}")


def build_artifact_store(root: str | Path | None = None) -> ArtifactStorePort:
    directory = Path(
        root
        or os.getenv("SENTRIX_ARTIFACT_DIR")
        or (Path.home() / "sentrix-artifacts")
    )
    return FilesystemArtifactStore(directory)
