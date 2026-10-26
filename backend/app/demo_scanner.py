from __future__ import annotations

from .ports import ScanFinding, ScanJobContext, ScanResult

DEMO_TITLE = "Demo configuration exposure"
DEMO_EVIDENCE = (
    "No external target was contacted. This is deterministic demo output for "
    "the local SENTRIX workflow."
)


class DemoScannerAdapter:
    """Deterministic scanner stub used by the local demo."""

    adapter_code = "demo"

    def scan(self, job: ScanJobContext) -> ScanResult:
        finding = ScanFinding(
            title=DEMO_TITLE,
            severity="LOW",
            status="NEW",
            evidence=DEMO_EVIDENCE,
            notes=(
                "Synthetic finding produced by the demo adapter; not a real "
                "scanner result."
            ),
        )
        return ScanResult(findings=(finding,), adapter_code=self.adapter_code)
