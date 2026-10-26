"""Local GNN inference service for VM03.

POST /v1/score  {"source": "int f(...) {...}"}
Returns vulnerableProbability, model, threshold.
No target/network access; source-only scoring.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from predict import score

HOST = os.getenv("SENTRIX_GNN_HOST", "10.20.10.30")
PORT = int(os.getenv("SENTRIX_GNN_PORT", "8002"))
ARTIFACT = Path(
    os.getenv(
        "SENTRIX_GNN_ARTIFACT",
        str(Path.home() / "sentrix-gnn/artifacts/devign-gat/model.pt"),
    )
)


class Handler(BaseHTTPRequestHandler):
    server_version = "SENTRIXGNN/0.1"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._json(200, {"status": "ok", "service": "sentrix-gnn", "model": str(ARTIFACT)})
            return
        self._json(404, {"detail": "not found"})

    def do_POST(self):  # noqa: N802
        if self.path != "/v1/score":
            self._json(404, {"detail": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            source = payload["source"]
            if not isinstance(source, str) or not source.strip():
                raise ValueError("source must be non-empty")
            result = score(source, ARTIFACT)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"detail": str(exc)})
            return
        except Exception as exc:
            self._json(500, {"detail": f"score failed: {exc}"})
            return
        self._json(200, result)

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    print(f"SENTRIX GNN inference on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
