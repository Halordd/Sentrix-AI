from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.automation import sign_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engagement", required=True)
    parser.add_argument("--authorized-by", default="user-admin")
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--action-class", action="append", default=["READ_ONLY", "SAFE_POC"])
    parser.add_argument("--max-risk", type=int, default=1)
    parser.add_argument("--max-actions", type=int, default=10)
    parser.add_argument("--minutes", type=int, default=30)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    manifest = {
        "engagementId": args.engagement,
        "authorizedBy": args.authorized_by,
        "validFrom": now.isoformat(),
        "validUntil": (now + timedelta(minutes=args.minutes)).isoformat(),
        "targets": args.target,
        "excludedTargets": [],
        "allowedActionClasses": args.action_class,
        "maxRiskTier": args.max_risk,
        "maxActions": args.max_actions,
        "maxDurationMinutes": args.minutes,
        "snapshotRequired": True,
        "humanOnLoop": True,
    }
    print(json.dumps(sign_manifest(manifest), indent=2))


if __name__ == "__main__":
    main()
