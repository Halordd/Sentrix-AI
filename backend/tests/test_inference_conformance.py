from __future__ import annotations

from app.mock_inference import MockInferenceAdapter
from app.ports import InferenceContext


def test_mock_inference_critical_confidence():
    result = MockInferenceAdapter().analyze(
        InferenceContext(
            finding_id="finding-bola",
            title="Broken object-level authorization",
            severity="CRITICAL",
        )
    )
    assert result.confidence == 0.91
    assert result.model == "SENTRIX Risk Engine"
    assert result.version == "4.8.2"
    assert result.simulated is True
    assert result.input_hash
    assert result.summary


def test_mock_inference_other_severities():
    for severity in ("HIGH", "MEDIUM", "LOW"):
        result = MockInferenceAdapter().analyze(
            InferenceContext(
                finding_id="finding-test",
                title="Test finding",
                severity=severity,
            )
        )
        assert result.confidence == 0.76
        assert result.simulated is True
