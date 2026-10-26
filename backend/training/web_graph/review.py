"""Human review workflow for the 20-record web corpus.

The harness can only produce rule labels. This CLI requires a named human
reviewer to accept or reject each candidate before it becomes a training label.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--show", metavar="ID")
    parser.add_argument("--accept", metavar="ID")
    parser.add_argument("--reject", metavar="ID")
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--from-csv",
        metavar="FILE",
        help="CSV with id,human_decision,reviewer,note columns",
    )
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--allow-non-200", action="store_true")
    args = parser.parse_args()
    path = Path(args.corpus)
    data = load(path)

    if args.list:
        for record in data["records"]:
            print(
                record["id"],
                record.get("reviewStatus", "RULE_ONLY"),
                record["label"],
                record["title"],
            )
        return

    if args.show:
        for record in data["records"]:
            if record["id"] == args.show:
                print(json.dumps(record, indent=2))
                return
        raise SystemExit(f"record not found: {args.show}")

    if args.audit:
        invalid = [
            record
            for record in data["records"]
            if record.get("reviewStatus") == "HUMAN_VERIFIED"
            and int(record.get("evidence", {}).get("status", 0)) != 200
        ]
        print(
            json.dumps(
                {
                    "audit": "HUMAN_VERIFIED with HTTP status != 200",
                    "count": len(invalid),
                    "records": [
                        {
                            "id": record["id"],
                            "status": record["evidence"].get("status"),
                            "title": record["title"],
                            "reviewedBy": record.get("reviewedBy"),
                        }
                        for record in invalid
                    ],
                },
                indent=2,
            )
        )
        return

    if args.from_csv:
        by_id = {record["id"]: record for record in data["records"]}
        applied = 0
        skipped = []
        with Path(args.from_csv).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                decision = (row.get("human_decision") or "").strip().lower()
                if decision not in {"accept", "reject"}:
                    continue
                reviewer = (row.get("reviewer") or args.reviewer).strip()
                if not reviewer:
                    raise SystemExit(f"reviewer missing for {row.get('id')}")
                record = by_id.get((row.get("id") or "").strip())
                if record is None:
                    raise SystemExit(f"record not found: {row.get('id')}")
                status = int(record.get("evidence", {}).get("status", 0))
                if decision == "accept" and status != 200 and not args.allow_non_200:
                    skipped.append({"id": record["id"], "status": status, "reason": "accept requires HTTP 200"})
                    continue
                record["label"] = 1 if decision == "accept" else 0
                record["verified"] = decision == "accept"
                record["reviewStatus"] = (
                    "HUMAN_VERIFIED" if decision == "accept" else "HUMAN_REJECTED"
                )
                record["reviewedBy"] = reviewer
                record["reviewedAt"] = datetime.now(timezone.utc).isoformat()
                record["reviewNote"] = row.get("note") or args.note
                applied += 1
        save(path, data)
        print(json.dumps({"applied": applied, "skipped": skipped, "corpus": str(path)}))
        return

    target_id = args.accept or args.reject
    if not target_id:
        raise SystemExit("use --list, --accept ID, --reject ID, or --from-csv FILE")
    if not args.reviewer.strip():
        raise SystemExit("--reviewer is required for human review")
    for record in data["records"]:
        if record["id"] == target_id:
            if (
                args.accept
                and int(record.get("evidence", {}).get("status", 0)) != 200
                and not args.allow_non_200
            ):
                raise SystemExit(
                    "refusing to accept non-200 evidence; use --allow-non-200 only with a documented reason"
                )
            record["label"] = 1 if args.accept else 0
            record["verified"] = bool(args.accept)
            record["reviewStatus"] = "HUMAN_VERIFIED" if args.accept else "HUMAN_REJECTED"
            record["reviewedBy"] = args.reviewer.strip()
            record["reviewedAt"] = datetime.now(timezone.utc).isoformat()
            record["reviewNote"] = args.note
            break
    else:
        raise SystemExit(f"record not found: {target_id}")
    save(path, data)
    print(json.dumps({"id": target_id, "status": record["reviewStatus"], "reviewer": args.reviewer}))


if __name__ == "__main__":
    main()
