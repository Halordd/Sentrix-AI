from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ScanJobContext:
    job_id: str
    project_id: str
    target_id: str
    target_name: str
    target_scope: str


@dataclass(frozen=True)
class ScanFinding:
    title: str
    severity: str
    status: str
    evidence: str
    notes: str


@dataclass(frozen=True)
class ScanResult:
    findings: tuple[ScanFinding, ...]
    adapter_code: str = "demo"


@dataclass(frozen=True)
class InferenceContext:
    finding_id: str
    title: str
    severity: str


@dataclass(frozen=True)
class InferenceResult:
    model: str
    version: str
    confidence: float
    summary: str
    limitations: str
    input_hash: str
    latency_ms: int
    simulated: bool = True


class ScannerPort(Protocol):
    def scan(self, job: ScanJobContext) -> ScanResult: ...


class InferencePort(Protocol):
    def analyze(self, context: InferenceContext) -> InferenceResult: ...


class ArtifactStorePort(Protocol):
    def put(self, data: bytes) -> str: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class ExecutionBackend(Protocol):
    def run(self, command: list[str], timeout_seconds: int, cwd: Path) -> int: ...
