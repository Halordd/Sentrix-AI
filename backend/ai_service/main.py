from __future__ import annotations

import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "10.20.10.30"
PORT = 8001
MODEL = "sentrix-ai-mock"
VERSION = "0.1.0"


class Handler(BaseHTTPRequestHandler):
    server_version = "SENTRIXAI/0.1"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"status": "ok", "service": "sentrix-ai-mock"})
            return
        self._json(404, {"detail": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/analyze":
            self._json(404, {"detail": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"detail": "invalid json"})
            return
        title = str(payload.get("title", "finding"))
        severity = str(payload.get("severity", "UNKNOWN"))
        summary = (
            f"Mock AI assessment for {severity} finding '{title}': validate the "
            "evidence, confirm scope, and require analyst review before remediation."
        )
        self._json(
            200,
            {
                "status": "COMPLETED",
                "model": MODEL,
                "version": VERSION,
                "confidence": 0.91,
                "summary": summary,
                "limitations": "Deterministic mock; no trained model or external inference.",
                "inputHash": hashlib.sha256(
                    f"{title}:{severity}".encode()
                ).hexdigest(),
                "latencyMs": 12,
                "simulated": True,
            },
        )

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    print(f"sentrix-ai-mock listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
