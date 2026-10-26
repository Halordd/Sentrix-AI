"""Sandbox executors for L3-C.

R0 is read-only. R1 is a non-destructive security-header boundary check. There
is deliberately no shell, no write method and no arbitrary path.
"""
from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .automation import CATALOG, ActionTier, Decision


class ExecutorError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExecutionResult:
    action: str
    target: str
    status: int
    headers: dict[str, str]
    body_sha256: str
    bytes_read: int
    observations: dict = field(default_factory=dict)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ExecutorError("redirects are not allowed in the sandbox")


class SandboxHttp:
    def __init__(self, timeout_seconds: float = 3.0, max_bytes: int = 65_536) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self._opener = urllib.request.build_opener(NoRedirect)

    def url(self, target: str) -> str:
        candidate = target if "://" in target else f"http://{target}/"
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"}:
            raise ExecutorError("only http/https targets are allowed")
        if not parsed.hostname:
            raise ExecutorError("target host is required")
        if parsed.username or parsed.password:
            raise ExecutorError("credentials in target are not allowed")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ExecutorError("only the root path is allowed for sandbox checks")
        return candidate.rstrip("/") + "/"

    def _allowed(self, url: str, allowed_hosts: set[str] | None) -> None:
        if allowed_hosts is None:
            return
        host = (urlparse(url).hostname or "").lower()
        if host not in {value.lower() for value in allowed_hosts}:
            raise ExecutorError("target host is outside the signed allowlist")

    def capture(
        self, target: str, allowed_hosts: set[str] | None = None
    ) -> ExecutionResult:
        url = self.url(target)
        self._allowed(url, allowed_hosts)
        return self._fetch(url, "snapshot", target)

    def _fetch(self, url: str, action: str, target: str) -> ExecutionResult:
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "SENTRIX-Sandbox/1.0", "Accept": "*/*"},
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                body = response.read(self.max_bytes)
                headers = {
                    key.lower(): value
                    for key, value in response.headers.items()
                    if key.lower()
                    in {
                        "content-type",
                        "content-length",
                        "server",
                        "x-powered-by",
                        "date",
                        "x-content-type-options",
                        "x-frame-options",
                        "content-security-policy",
                        "strict-transport-security",
                    }
                }
                return ExecutionResult(
                    action=action,
                    target=target,
                    status=response.status,
                    headers=headers,
                    body_sha256=hashlib.sha256(body).hexdigest(),
                    bytes_read=len(body),
                )
        except urllib.error.HTTPError as error:
            body = error.read(self.max_bytes)
            return ExecutionResult(
                action=action,
                target=target,
                status=error.code,
                headers={},
                body_sha256=hashlib.sha256(body).hexdigest(),
                bytes_read=len(body),
            )
        except ExecutorError:
            raise
        except Exception as exc:
            raise ExecutorError(f"sandbox request failed: {exc}") from exc


class ReadOnlyExecutor(SandboxHttp):
    def execute(
        self,
        decision: Decision,
        target: str,
        allowed_hosts: set[str] | None = None,
    ) -> ExecutionResult:
        if not decision.allowed or decision.approval_required:
            raise ExecutorError(decision.reason)
        if decision.action not in {"read.target_metadata", "read.response_headers"}:
            raise ExecutorError("R0 executor only supports catalogued read-only actions")
        spec = CATALOG.get(decision.action or "")
        if spec is None or spec.tier != ActionTier.READ_ONLY:
            raise ExecutorError("action is not an R0 read-only action")
        url = self.url(target)
        self._allowed(url, allowed_hosts)
        return self._fetch(url, decision.action, target)


class SafePocExecutor(SandboxHttp):
    """R1: non-destructive security-header boundary validation."""

    REQUIRED_HEADERS = (
        "content-security-policy",
        "x-content-type-options",
        "x-frame-options",
        "strict-transport-security",
    )

    def execute(
        self,
        decision: Decision,
        target: str,
        allowed_hosts: set[str] | None = None,
    ) -> ExecutionResult:
        if not decision.allowed or decision.approval_required:
            raise ExecutorError(decision.reason)
        if decision.action != "safe.poc_boundary_check":
            raise ExecutorError("R1 executor only supports the safe boundary check")
        spec = CATALOG.get(decision.action)
        if spec is None or spec.tier != ActionTier.SAFE_POC:
            raise ExecutorError("action is not an R1 safe PoC")
        url = self.url(target)
        self._allowed(url, allowed_hosts)
        result = self._fetch(url, decision.action, target)
        missing = [
            header for header in self.REQUIRED_HEADERS if header not in result.headers
        ]
        return ExecutionResult(
            action=result.action,
            target=result.target,
            status=result.status,
            headers=result.headers,
            body_sha256=result.body_sha256,
            bytes_read=result.bytes_read,
            observations={
                "check": "security_headers",
                "missing": missing,
                "nonDestructive": True,
            },
        )
