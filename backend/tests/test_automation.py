from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.automation import evaluate, sign_manifest


def manifest(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "engagementId": "engagement-test",
        "authorizedBy": "user-admin",
        "validFrom": (now - timedelta(minutes=5)).isoformat(),
        "validUntil": (now + timedelta(minutes=30)).isoformat(),
        "targets": ["10.20.20.20"],
        "excludedTargets": [],
        "allowedActionClasses": ["READ_ONLY", "SAFE_POC"],
        "maxRiskTier": 1,
        "maxActions": 5,
        "maxDurationMinutes": 30,
        "snapshotRequired": True,
        "humanOnLoop": True,
    }
    payload.update(overrides)
    return sign_manifest(payload)


def test_read_only_action_is_auto_allowed():
    decision = evaluate(manifest(), "read.target_metadata", "10.20.20.20")
    assert decision.allowed is True
    assert decision.approval_required is False
    assert decision.tier == 0


def test_safe_poc_requires_snapshot_and_is_auto_allowed():
    allowed = evaluate(manifest(), "safe.poc_boundary_check", "10.20.20.20")
    assert allowed.allowed is True
    assert allowed.approval_required is False
    denied = evaluate(
        manifest(snapshotRequired=False),
        "safe.poc_boundary_check",
        "10.20.20.20",
    )
    assert denied.allowed is False
    assert "snapshot" in denied.reason


def test_state_change_requires_approval():
    decision = evaluate(
        manifest(maxRiskTier=2, allowedActionClasses=["READ_ONLY", "SAFE_POC", "STATE_CHANGING"]),
        "state.change_user",
        "10.20.20.20",
    )
    assert decision.allowed is False
    assert decision.approval_required is True


def test_prohibited_and_out_of_scope_are_denied():
    prohibited = evaluate(manifest(), "prohibited.persistence", "10.20.20.20")
    assert prohibited.allowed is False
    assert "prohibited" in prohibited.reason

    out_of_scope = evaluate(manifest(), "read.target_metadata", "10.20.20.99")
    assert out_of_scope.allowed is False
    assert "scope" in out_of_scope.reason

    excluded = evaluate(
        manifest(excludedTargets=["10.20.20.20"]), "read.target_metadata", "10.20.20.20"
    )
    assert excluded.allowed is False
    assert "excluded" in excluded.reason


def test_expired_and_tampered_manifests_are_rejected():
    expired = manifest(
        validFrom=(datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        validUntil=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    )
    assert evaluate(expired, "read.target_metadata", "10.20.20.20").allowed is False

    tampered = manifest()
    tampered["targets"] = ["10.20.20.99"]
    decision = evaluate(tampered, "read.target_metadata", "10.20.20.99")
    assert decision.allowed is False
    assert "signature" in decision.reason

    assert evaluate(manifest(), "read.target_metadata", "10.20.20.20", used_actions=5).allowed is False
