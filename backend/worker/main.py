from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "10.20.10.40"
PORT = 8080


class Handler(BaseHTTPRequestHandler):
    server_version = "SENTRIXWorker/0.1"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/health", "/ready"}:
            self._json(
                200,
                {
                    "status": "ok",
                    "service": "sentrix-worker",
                    "mode": "placeholder",
                    "host": HOST,
                },
            )
            return
        self._json(404, {"detail": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    print(f"sentrix-worker placeholder listening on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
