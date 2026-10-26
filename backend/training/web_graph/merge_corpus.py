"""Merge the unauth corpus and authenticated BOLA corpus."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    base = json.loads(Path("web_corpus.json").read_text())
    bola = json.loads(Path("bola_corpus.json").read_text())
    records = base["records"] + bola["records"]
    Path("web_corpus_combined.json").write_text(
        json.dumps({"base": base["base"], "records": records}, indent=2)
    )
    print(
        json.dumps(
            {
                "output": "web_corpus_combined.json",
                "records": len(records),
                "base": len(base["records"]),
                "bola": len(bola["records"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
