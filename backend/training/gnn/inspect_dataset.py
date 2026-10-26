from __future__ import annotations

import json
import sys
from pathlib import Path


def inspect(path: Path) -> None:
    text = path.read_text()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = [json.loads(line) for line in text.splitlines() if line.strip()]
    print(f"file={path.name} type={type(data).__name__}")
    if isinstance(data, dict):
        print("keys", list(data)[:10])
        for key, value in data.items():
            if isinstance(value, list):
                print(f"{key}: {len(value)}")
                if value:
                    print(" first keys", list(value[0])[:12] if isinstance(value[0], dict) else type(value[0]))
                    print(json.dumps(value[0], ensure_ascii=False)[:500])
                break
    elif isinstance(data, list):
        print("count", len(data))
        print("first keys", list(data[0])[:12] if data and isinstance(data[0], dict) else type(data[0]))
        print(json.dumps(data[0], ensure_ascii=False)[:500])


if __name__ == "__main__":
    for name in sys.argv[1:]:
        inspect(Path(name))
