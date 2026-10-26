"""Compare L2 and L3-C policy outcomes on a deterministic candidate set.

This is a policy simulation, not a live execution benchmark. It shows how many
actions would auto-run vs need approval/denial; it does not contact a target.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.automation import evaluate, sign_manifest

NOW = datetime.now(timezone.utc)
MANIFEST = sign_manifest(
    {
        "engagementId": "simulation",
        "authorizedBy": "user-admin",
        "validFrom": (NOW - timedelta(minutes=2)).isoformat(),
        "validUntil": (NOW + timedelta(hours=1)).isoformat(),
        "targets": ["10.20.20.20"],
        "excludedTargets": [],
        "allowedActionClasses": ["READ_ONLY", "SAFE_POC", "STATE_CHANGING"],
        "maxRiskTier": 2,
        "maxActions": 50,
        "maxDurationMinutes": 60,
        "snapshotRequired": True,
        "humanOnLoop": True,
    }
)

CANDIDATES = [
    *[("read.target_metadata", 0.98)] * 8,
    *[("read.response_headers", 0.90)] * 5,
    *[("safe.poc_boundary_check", 0.80)] * 4,
    *[("state.change_user", 0.60)] * 2,
    *[("prohibited.persistence", 0.99)] * 1,
]


def main() -> None:
    decisions = [
        (action, score, evaluate(MANIFEST, action, "10.20.20.20"))
        for action, score in CANDIDATES
    ]
    l2 = {
        "manual_reviews": len(decisions),
        "auto_actions": 0,
        "approval_actions": len(decisions),
        "denied_actions": 0,
    }
    l3 = {
        "manual_reviews": 0,
        "auto_actions": sum(1 for _, _, d in decisions if d.allowed and not d.approval_required),
        "approval_actions": sum(1 for _, _, d in decisions if d.approval_required),
        "denied_actions": sum(1 for _, _, d in decisions if not d.allowed and not d.approval_required),
    }
    print(
        json.dumps(
            {
                "scope": "policy simulation; no target contacted",
                "manifest": MANIFEST["engagementId"],
                "candidates": len(decisions),
                "l2": l2,
                "l3c": l3,
                "decisions": [
                    {
                        "action": action,
                        "score": score,
                        "allowed": d.allowed,
                        "approvalRequired": d.approval_required,
                        "reason": d.reason,
                    }
                    for action, score, d in decisions
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
