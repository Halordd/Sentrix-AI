from __future__ import annotations

import hashlib

from .ports import InferenceContext, InferenceResult

MODEL = "SENTRIX Risk Engine"
VERSION = "4.8.2"
LIMITATIONS = (
    "Deterministic mock inference for local demonstration only; not a trained "
    "model or production measurement."
)


class MockInferenceAdapter:
    """Conforms to AT-4.3: 0.91 for CRITICAL, 0.76 otherwise."""

    adapter_code = "mock-inference"

    def analyze(self, context: InferenceContext) -> InferenceResult:
        confidence = 0.91 if context.severity == "CRITICAL" else 0.76
        summary = (
            f"Mock risk summary for {context.severity} finding '{context.title}': "
            "review the evidence and confirm scope before remediation."
        )
        digest = hashlib.sha256(
            f"{context.title}:{context.severity}".encode()
        ).hexdigest()
        return InferenceResult(
            model=MODEL,
            version=VERSION,
            confidence=confidence,
            summary=summary,
            limitations=LIMITATIONS,
            input_hash=digest,
            latency_ms=420,
            simulated=True,
        )
