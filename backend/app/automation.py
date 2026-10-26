"""L3-C automation policy.

This module deliberately does **not** execute exploitation. It decides whether a
catalogued action is allowed under a signed engagement manifest. Execution, if
added later, must go through the sandbox and approval flow described in
docs/phase2/26-l3-conditional-automation.md.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum


class ActionTier(IntEnum):
    READ_ONLY = 0
    SAFE_POC = 1
    STATE_CHANGING = 2
    PROHIBITED = 3


@dataclass(frozen=True)
class ActionSpec:
    code: str
    action_class: str
    tier: ActionTier
    description: str


# Only catalogued actions are eligible. There is intentionally no arbitrary
# shell/payload action in this table.
CATALOG: dict[str, ActionSpec] = {
    "read.target_metadata": ActionSpec(
        "read.target_metadata", "READ_ONLY", ActionTier.READ_ONLY,
        "Read target metadata through an allowlisted, non-destructive probe.",
    ),
    "read.response_headers": ActionSpec(
        "read.response_headers", "READ_ONLY", ActionTier.READ_ONLY,
        "Capture response headers for evidence.",
    ),
    "safe.poc_boundary_check": ActionSpec(
        "safe.poc_boundary_check", "SAFE_POC", ActionTier.SAFE_POC,
        "Run a non-destructive authorization-boundary validation.",
    ),
    "state.change_user": ActionSpec(
        "state.change_user", "STATE_CHANGING", ActionTier.STATE_CHANGING,
        "State-changing action; always needs human approval.",
    ),
    "prohibited.persistence": ActionSpec(
        "prohibited.persistence", "PROHIBITED", ActionTier.PROHIBITED,
        "Persistence/evasion/exfiltration class; never allowed.",
    ),
}

MANIFEST_FIELDS = {
    "engagementId",
    "authorizedBy",
    "validFrom",
    "validUntil",
    "targets",
    "excludedTargets",
    "allowedActionClasses",
    "maxRiskTier",
    "maxActions",
    "maxDurationMinutes",
    "snapshotRequired",
    "humanOnLoop",
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    approval_required: bool
    reason: str
    tier: int | None = None
    action: str | None = None


def _secret() -> str:
    return os.getenv("SENTRIX_AUTOMATION_SECRET", "sentrix-local-automation-secret")


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def sign_manifest(manifest: dict, secret: str | None = None) -> dict:
    body = {key: value for key, value in manifest.items() if key != "signature"}
    signature = hmac.new(
        (secret or _secret()).encode(), canonical(body), hashlib.sha256
    ).hexdigest()
    return {**body, "signature": signature}


def verify_manifest(manifest: dict, secret: str | None = None) -> None:
    if not isinstance(manifest, dict) or "signature" not in manifest:
        raise ValueError("manifest signature is required")
    body = {key: value for key, value in manifest.items() if key != "signature"}
    missing = MANIFEST_FIELDS - set(body)
    if missing:
        raise ValueError(f"manifest missing fields: {sorted(missing)}")
    expected = hmac.new(
        (secret or _secret()).encode(), canonical(body), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, str(manifest["signature"])):
        raise ValueError("manifest signature is invalid")


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def evaluate(
    manifest: dict,
    action_code: str,
    target: str,
    used_actions: int = 0,
    now: datetime | None = None,
) -> Decision:
    try:
        verify_manifest(manifest)
    except ValueError as exc:
        return Decision(False, False, f"manifest rejected: {exc}")
    current = now or datetime.now(timezone.utc)
    try:
        valid_from = _parse_time(manifest["validFrom"])
        valid_until = _parse_time(manifest["validUntil"])
    except (TypeError, ValueError):
        return Decision(False, False, "invalid manifest time window")
    if current < valid_from or current > valid_until:
        return Decision(False, False, "manifest is outside its validity window")
    if target in (manifest.get("excludedTargets") or []):
        return Decision(False, False, "target is explicitly excluded")
    if target not in (manifest.get("targets") or []):
        return Decision(False, False, "target is outside the signed scope")
    action = CATALOG.get(action_code)
    if action is None:
        return Decision(False, False, "action is not in the catalog")
    if used_actions >= int(manifest.get("maxActions", 0)):
        return Decision(False, False, "action budget exhausted")
    if action.tier == ActionTier.PROHIBITED:
        return Decision(False, False, "prohibited action class", action.tier, action.code)
    if action.tier > int(manifest.get("maxRiskTier", 0)):
        return Decision(False, False, "action tier exceeds manifest maximum", action.tier, action.code)
    if action.action_class not in (manifest.get("allowedActionClasses") or []):
        return Decision(False, False, "action class is not pre-approved", action.tier, action.code)
    if action.tier >= ActionTier.STATE_CHANGING:
        return Decision(False, True, "state-changing action requires human approval", action.tier, action.code)
    if action.tier == ActionTier.SAFE_POC and not bool(manifest.get("snapshotRequired", False)):
        return Decision(False, False, "safe PoC requires snapshot rollback", action.tier, action.code)
    return Decision(True, False, "allowed by signed manifest", action.tier, action.code)
