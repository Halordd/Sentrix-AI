from __future__ import annotations

import pytest

from app.demo_scanner import DEMO_EVIDENCE, DEMO_TITLE, DemoScannerAdapter
from app.ports import ScanFinding, ScanJobContext, ScanResult


class BrokenScannerAdapter:
    adapter_code = "broken"

    def scan(self, job: ScanJobContext) -> ScanResult:
        return ScanResult(findings=(), adapter_code=self.adapter_code)


def assert_demo_contract(adapter) -> None:
    result = adapter.scan(
        ScanJobContext(
            job_id="scan-test",
            project_id="project-atlas",
            target_id="target-atlas-api",
            target_name="api.atlas.example",
            target_scope="https://api.atlas.example/v2/*",
        )
    )

    assert result.adapter_code == "demo"
    assert len(result.findings) == 1

    finding = result.findings[0]
    assert finding.title == DEMO_TITLE == "Demo configuration exposure"
    assert finding.severity == "LOW"
    assert finding.status == "NEW"
    assert "No external target was contacted" in DEMO_EVIDENCE
    assert "No external target was contacted" in finding.evidence
    assert finding.notes


def test_demo_scanner_conformance():
    assert_demo_contract(DemoScannerAdapter())


def test_broken_scanner_fails_conformance():
    with pytest.raises(AssertionError):
        assert_demo_contract(BrokenScannerAdapter())
