"""Merge reviewed batch 2 into the main web corpus."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    base = json.loads(Path("web_corpus_combined.json").read_text())
    batch2 = json.loads(Path("web_corpus_batch2.json").read_text())
    records = base["records"] + batch2["records"]
    Path("web_corpus_v2.json").write_text(json.dumps({"base": base["base"], "records": records}, indent=2))
    print(
        json.dumps(
            {
                "output": "web_corpus_v2.json",
                "records": len(records),
                "base": len(base["records"]),
                "batch2": len(batch2["records"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
