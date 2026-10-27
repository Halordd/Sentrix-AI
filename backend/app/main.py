from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from dataclasses import asdict
from datetime import date, datetime, timezone, timedelta
from typing import Literal
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from .adapters import build_artifact_store, build_inference, build_scanner
from .artifact_store import ArtifactStoreError
from .automation import CATALOG, evaluate as evaluate_automation
from .automation_executor import (
    ExecutorError,
    ReadOnlyExecutor,
    SafePocExecutor,
    SandboxHttp,
)
from .auth import (
    hash_password,
    is_token_revoked,
    issue_token,
    revoke_token,
    verify_password,
    verify_token,
)
from .bootstrap import FINDING_STATUS, SCAN_PROFILE, SCAN_STATUS, SEVERITY, build_bootstrap
from .db import database_ping, get_engine
from .ports import InferenceContext, ScanJobContext
from .rate_limit import SlidingWindowLimiter

app = FastAPI(
    title="SENTRIX API",
    version="0.1.0",
    description="Local SENTRIX backend.",
)


@app.exception_handler(ExecutorError)
async def executor_error_handler(_request: Request, exc: ExecutorError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


class LoginInput(BaseModel):
    email: str
    password: str


PUBLIC_API_PATHS = {"/api/v1/auth/login"}
API_LIMITER = SlidingWindowLimiter(limit=600, window_seconds=60)
LOGIN_LIMITER = SlidingWindowLimiter(limit=60, window_seconds=60)


@app.middleware("http")
async def require_api_auth(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/v1/"):
        client = request.headers.get("X-Real-IP") or (
            request.client.host if request.client else "unknown"
        )
        limiter = LOGIN_LIMITER if path in PUBLIC_API_PATHS else API_LIMITER
        if not limiter.allow(client):
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
                headers={"Retry-After": "60"},
            )
    if path.startswith("/api/v1/") and path not in PUBLIC_API_PATHS:
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if is_token_revoked(token):
            return JSONResponse(status_code=401, content={"detail": "authentication required"})
        user = verify_token(token)
        if user is None:
            return JSONResponse(status_code=401, content={"detail": "authentication required"})
        if request.method in {"POST", "PATCH", "PUT", "DELETE"} and user.get(
            "role"
        ) not in {"ANALYST", "ADMIN"}:
            return JSONResponse(status_code=403, content={"detail": "write access denied"})
        request.state.user = user
    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sentrix-api"}


@app.get("/health/db")
def health_db() -> dict[str, str]:
    try:
        database_ping()
    except Exception as exc:  # pragma: no cover - surfaced through the endpoint
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc
    return {"status": "ok", "database": "sentrix"}


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    owner: str | None = None
    scope: str | None = None


class TargetInput(BaseModel):
    projectId: str
    name: str = Field(min_length=1, max_length=200)
    type: str = "Web"
    scope: str = ""
    authorizationConfirmed: bool = False


class ScanInput(BaseModel):
    targetId: str
    name: str = Field(min_length=1, max_length=160)
    profile: str = "External attack surface"


class FindingStatusInput(BaseModel):
    status: Literal[
        "NEW",
        "CONFIRMED",
        "IN_PROGRESS",
        "RESOLVED",
        "REOPENED",
        "ACCEPTED_RISK",
        "FALSE_POSITIVE",
    ]


class TransitionInput(BaseModel):
    to: Literal[
        "CONFIRMED",
        "IN_PROGRESS",
        "RESOLVED",
        "REOPENED",
        "ACCEPTED_RISK",
        "FALSE_POSITIVE",
    ]
    reason: str | None = None


class RemediationInput(BaseModel):
    assignee: str | None = None
    dueDate: str | None = None
    notes: str = ""


class VerificationInput(BaseModel):
    outcome: Literal["VERIFIED", "REJECTED"] = "VERIFIED"
    method: Literal["RESCAN", "AUTOMATED_TEST", "MANUAL_REVIEW"] = "MANUAL_REVIEW"
    notes: str = ""


class AutomationCheckInput(BaseModel):
    manifest: dict
    actionCode: str
    target: str
    usedActions: int = 0


class AutomationCandidateInput(BaseModel):
    findingId: str
    target: str
    actionCode: str
    score: float = 0.0


class AutomationRequestInput(BaseModel):
    manifest: dict


class AutomationDecisionInput(BaseModel):
    reason: str = ""


class AutomationExecuteInput(BaseModel):
    manifest: dict


class ReportInput(BaseModel):
    projectId: str
    title: str = Field(min_length=1, max_length=200)
    scanId: str | None = None


class MembershipInput(BaseModel):
    userId: str
    role: Literal["OWNER", "ANALYST", "VIEWER"]


class MembershipRoleInput(BaseModel):
    role: Literal["OWNER", "ANALYST", "VIEWER"]


class UserInput(BaseModel):
    displayName: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=200)
    role: Literal["ADMIN", "ANALYST", "VIEWER"] = "ANALYST"
    password: str = Field(min_length=8, max_length=200)


class UserPatch(BaseModel):
    displayName: str | None = None
    role: Literal["ADMIN", "ANALYST", "VIEWER"] | None = None
    isActive: bool | None = None


PROFILE_IDS = {
    "external attack surface": "external_attack_surface",
    "api authorization": "api_authorization",
    "cloud configuration": "cloud_configuration",
}
TARGET_TYPES = {"web": "WEB", "api": "API", "cloud": "CLOUD"}
TRANSITIONS = {
    "NEW": {"CONFIRMED", "FALSE_POSITIVE", "ACCEPTED_RISK"},
    "CONFIRMED": {"ACCEPTED_RISK", "FALSE_POSITIVE"},
    "IN_PROGRESS": {"REOPENED", "ACCEPTED_RISK"},
    "REOPENED": {"CONFIRMED", "ACCEPTED_RISK", "FALSE_POSITIVE"},
    "RESOLVED": {"REOPENED"},
    "ACCEPTED_RISK": {"REOPENED"},
    "FALSE_POSITIVE": {"REOPENED"},
}
REASON_REQUIRED = {
    ("NEW", "FALSE_POSITIVE"),
    ("NEW", "ACCEPTED_RISK"),
    ("CONFIRMED", "FALSE_POSITIVE"),
    ("CONFIRMED", "ACCEPTED_RISK"),
    ("IN_PROGRESS", "REOPENED"),
    ("IN_PROGRESS", "ACCEPTED_RISK"),
    ("REOPENED", "ACCEPTED_RISK"),
    ("REOPENED", "FALSE_POSITIVE"),
    ("RESOLVED", "REOPENED"),
    ("ACCEPTED_RISK", "REOPENED"),
    ("FALSE_POSITIVE", "REOPENED"),
}
STATUS_LABEL = {
    "NEW": "New",
    "CONFIRMED": "Confirmed",
    "IN_PROGRESS": "In Progress",
    "RESOLVED": "Resolved",
    "REOPENED": "Reopened",
    "ACCEPTED_RISK": "Accepted Risk",
    "FALSE_POSITIVE": "False Positive",
}
SEVERITY_LABEL = {
    "CRITICAL": "Critical",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
}


def _audit(
    connection,
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    resource_name: str,
    outcome: str = "SUCCESS",
    metadata: dict | None = None,
) -> None:
    actor = connection.execute(
        text("SELECT display_name FROM app_user WHERE id = :id"),
        {"id": user_id},
    ).scalar_one()
    connection.execute(
        text(
            """
            INSERT INTO audit_event
                (id, occurred_at, actor_id, actor_label, action, resource_type,
                 resource_id, resource_name, outcome, request_id, metadata)
            VALUES (:id, :now, :actor_id, :actor_label, :action, :resource_type,
                    :resource_id, :resource_name, :outcome, 'api', CAST(:metadata AS jsonb))
            """
        ),
        {
            "id": f"audit-{uuid4().hex[:12]}",
            "now": datetime.now(timezone.utc),
            "actor_id": user_id,
            "actor_label": actor,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "outcome": outcome,
            "metadata": json.dumps(metadata or {}),
        },
    )


def _require_admin(request: Request) -> None:
    if request.state.user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="admin access required")


def _auth_audit(
    email: str,
    action: str,
    outcome: str,
    user_id: str | None = None,
) -> None:
    try:
        with get_engine().begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO audit_event
                        (id, occurred_at, actor_id, actor_label, action, resource_type,
                         resource_id, resource_name, outcome, request_id, metadata)
                    VALUES (:id, :now, :actor_id, :actor_label, :action, 'AUTH',
                            :resource_id, :resource_name, :outcome, 'api', CAST(:metadata AS jsonb))
                    """
                ),
                {
                    "id": f"audit-{uuid4().hex[:12]}",
                    "now": datetime.now(timezone.utc),
                    "actor_id": user_id,
                    "actor_label": email,
                    "action": action,
                    "resource_id": email,
                    "resource_name": email,
                    "outcome": outcome,
                    "metadata": "{}",
                },
            )
    except Exception as exc:
        print(f"auth audit failed: {exc}", flush=True)


def _require_project_owner(connection, project_id: str, request: Request) -> None:
    if request.state.user.get("role") == "ADMIN":
        return
    user_id = request.state.user["sub"]
    project = connection.execute(
        text("SELECT id, owner_id FROM project WHERE id = :id"), {"id": project_id}
    ).first()
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    if project[1] == user_id:
        return
    membership = connection.execute(
        text(
            "SELECT role FROM project_member WHERE project_id = :project_id AND user_id = :user_id"
        ),
        {"project_id": project_id, "user_id": user_id},
    ).first()
    if membership is None or membership[0] != "OWNER":
        raise HTTPException(status_code=403, detail="project owner access required")


def _require_project_member(
    connection,
    project_id: str,
    request: Request,
    roles: set[str] | None = None,
) -> None:
    if request.state.user.get("role") == "ADMIN":
        return
    user_id = request.state.user["sub"]
    membership = connection.execute(
        text(
            "SELECT role FROM project_member WHERE project_id = :project_id AND user_id = :user_id"
        ),
        {"project_id": project_id, "user_id": user_id},
    ).first()
    if membership is None:
        owner_id = connection.execute(
            text("SELECT owner_id FROM project WHERE id = :project_id"),
            {"project_id": project_id},
        ).scalar_one_or_none()
        if owner_id == user_id:
            return
        raise HTTPException(status_code=404, detail="project not found")
    if roles is not None and membership[0] not in roles:
        raise HTTPException(status_code=403, detail="project role does not allow this action")


@app.post("/api/v1/auth/login")
def login(payload: LoginInput) -> dict:
    with get_engine().connect() as connection:
        user = connection.execute(
            text(
                """
                SELECT id, display_name, email, role, password_hash, is_active
                FROM app_user WHERE lower(email) = lower(:email)
                """
            ),
            {"email": payload.email.strip()},
        ).mappings().first()
    if user is None or not user["is_active"] or not verify_password(
        payload.password, user["password_hash"]
    ):
        _auth_audit(payload.email.strip(), "auth.login", "DENIED")
        raise HTTPException(status_code=401, detail="invalid credentials")
    _auth_audit(user["email"], "auth.login", "SUCCESS", user["id"])
    return {
        "token": issue_token(user["id"], user["role"]),
        "user": {
            "id": user["id"],
            "name": user["display_name"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.get("/api/v1/auth/me")
def me(request: Request) -> dict:
    user = request.state.user
    with get_engine().connect() as connection:
        row = connection.execute(
            text("SELECT id, display_name, email, role FROM app_user WHERE id = :id"),
            {"id": user["sub"]},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=401, detail="unknown user")
    return {
        "id": row["id"],
        "name": row["display_name"],
        "email": row["email"],
        "role": row["role"],
    }


@app.post("/api/v1/auth/logout", status_code=204)
def logout(request: Request) -> Response:
    header = request.headers.get("Authorization", "")
    token = header[7:] if header.startswith("Bearer ") else ""
    user = request.state.user
    with get_engine().connect() as connection:
        email = connection.execute(
            text("SELECT email FROM app_user WHERE id = :id"),
            {"id": user["sub"]},
        ).scalar_one()
    revoke_token(token)
    _auth_audit(email, "auth.logout", "SUCCESS", user["sub"])
    return Response(status_code=204)


@app.get("/api/v1/bootstrap")
def bootstrap() -> dict:
    return build_bootstrap()


@app.post("/api/v1/projects", status_code=201)
def create_project(payload: ProjectInput, request: Request) -> dict:
    project_id = f"project-{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    with get_engine().begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO project (id, name, owner_id, scope, status, created_on, created_at, updated_at)
                VALUES (:id, :name, :owner, :scope, 'ACTIVE', :created_on, :created_at, :created_at)
                """
            ),
            {
                "id": project_id,
                "name": payload.name.strip(),
                "owner": "user-maya",
                "scope": (payload.scope or "Not configured").strip(),
                "created_on": now.date(),
                "created_at": now,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "project.created",
            "PROJECT",
            project_id,
            payload.name.strip(),
            metadata={"scope": (payload.scope or "Not configured").strip()},
        )
    return {
        "id": project_id,
        "name": payload.name.strip(),
        "owner": payload.owner or "Maya Chen",
        "status": "Active",
        "scope": (payload.scope or "Not configured").strip(),
        "createdAt": now.date().isoformat(),
    }


@app.post("/api/v1/projects/{project_id}/archive")
def archive_project(project_id: str, request: Request) -> dict:
    now = datetime.now(timezone.utc)
    with get_engine().begin() as connection:
        project = connection.execute(
            text("SELECT id, name FROM project WHERE id = :id"),
            {"id": project_id},
        ).mappings().first()
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        _require_project_owner(connection, project_id, request)
        connection.execute(
            text(
                """
                UPDATE project
                SET status = CAST('ARCHIVED' AS project_status),
                    archived_at = COALESCE(archived_at, :now),
                    updated_at = :now
                WHERE id = :id
                """
            ),
            {"id": project_id, "now": now},
        )
        _audit(
            connection,
            request.state.user["sub"],
            "project.archived",
            "PROJECT",
            project_id,
            project["name"],
        )
    return {"id": project_id, "status": "Archived", "archivedAt": now.isoformat()}


@app.post("/api/v1/targets", status_code=201)
def create_target(payload: TargetInput, request: Request) -> dict:
    if not payload.authorizationConfirmed:
        raise HTTPException(status_code=400, detail="authorization confirmation is required")
    now = datetime.now(timezone.utc)
    target_id = f"target-{uuid4().hex[:12]}"
    auth_id = f"auth-{uuid4().hex[:12]}"
    with get_engine().begin() as connection:
        project = connection.execute(
            text("SELECT id FROM project WHERE id = :id"),
            {"id": payload.projectId},
        ).first()
        if project is None:
            raise HTTPException(status_code=400, detail="unknown project")
        connection.execute(
            text(
                """
                INSERT INTO target (id, project_id, name, type, scope, created_at, updated_at, created_by)
                VALUES (:id, :project_id, :name, :type, :scope, :created_at, :created_at, 'user-maya')
                """
            ),
            {
                "id": target_id,
                "project_id": payload.projectId,
                "name": payload.name.strip(),
                "type": TARGET_TYPES.get(payload.type.lower(), "WEB"),
                "scope": payload.scope.strip(),
                "created_at": now,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO target_authorization
                    (id, target_id, attested_by, attested_at, statement, scope_snapshot)
                VALUES (:id, :target_id, 'user-maya', :attested_at, :statement, :scope)
                """
            ),
            {
                "id": auth_id,
                "target_id": target_id,
                "attested_at": now,
                "statement": "I confirm I am authorized to test this target.",
                "scope": payload.scope.strip(),
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "target.created",
            "TARGET",
            target_id,
            payload.name.strip(),
            metadata={"projectId": payload.projectId, "scope": payload.scope.strip()},
        )
    return {
        "id": target_id,
        "projectId": payload.projectId,
        "name": payload.name.strip(),
        "type": payload.type,
        "authorized": True,
        "scope": payload.scope.strip(),
        "status": "Monitored",
    }


@app.get("/api/v1/scans/{scan_id}")
def get_scan(scan_id: str, request: Request) -> dict:
    with get_engine().connect() as connection:
        scan = connection.execute(
            text(
                """
                SELECT j.id, j.project_id, j.target_id, j.name, j.profile_id,
                       j.status, j.created_at,
                       r.id AS run_id, r.status AS run_status, r.progress,
                       r.attempt, r.started_at, r.finished_at, r.error_message
                FROM scan_job j
                LEFT JOIN scan_run r ON r.id = (
                    SELECT id FROM scan_run WHERE job_id = j.id
                    ORDER BY attempt DESC LIMIT 1
                )
                WHERE j.id = :id
                """
            ),
            {"id": scan_id},
        ).mappings().first()
        if scan is None:
            raise HTTPException(status_code=404, detail="scan not found")
        _require_project_member(connection, scan["project_id"], request)
        findings = connection.execute(
            text(
                """
                SELECT f.id, f.title, f.severity, f.status, f.notes, f.created_at,
                       e.content AS evidence
                FROM finding f
                LEFT JOIN evidence e ON e.finding_id = f.id
                WHERE f.job_id = :id ORDER BY f.created_at, f.id
                """
            ),
            {"id": scan_id},
        ).mappings().all()
    return {
        "id": scan["id"],
        "projectId": scan["project_id"],
        "targetId": scan["target_id"],
        "name": scan["name"],
        "profile": SCAN_PROFILE.get(scan["profile_id"], scan["profile_id"]),
        "status": SCAN_STATUS.get(scan["status"], scan["status"]),
        "progress": scan["progress"] or 0,
        "simulated": True,
        "createdAt": scan["created_at"].isoformat(),
        "completedAt": scan["finished_at"].isoformat() if scan["finished_at"] else None,
        "run": {
            "id": scan["run_id"],
            "status": scan["run_status"],
            "progress": scan["progress"] or 0,
            "attempt": scan["attempt"],
            "startedAt": scan["started_at"].isoformat() if scan["started_at"] else None,
            "finishedAt": scan["finished_at"].isoformat() if scan["finished_at"] else None,
            "error": scan["error_message"],
        } if scan["run_id"] else None,
        "findings": [
            {
                "id": row["id"],
                "scanId": scan_id,
                "projectId": scan["project_id"],
                "targetId": scan["target_id"],
                "title": row["title"],
                "severity": SEVERITY.get(row["severity"], row["severity"]),
                "status": FINDING_STATUS.get(row["status"], row["status"]),
                "evidence": row["evidence"] or "",
                "createdAt": row["created_at"].isoformat(),
                "notes": row["notes"] or "",
            }
            for row in findings
        ],
    }


@app.post("/api/v1/scans", status_code=201)
def create_scan(payload: ScanInput, request: Request) -> dict:
    now = datetime.now(timezone.utc)
    scan_id = f"scan-{uuid4().hex[:12]}"
    profile_id = PROFILE_IDS.get(payload.profile.lower(), "external_attack_surface")
    with get_engine().begin() as connection:
        target = connection.execute(
            text(
                """
                SELECT t.id, t.project_id, p.status AS project_status
                FROM target t JOIN project p ON p.id = t.project_id
                WHERE t.id = :id
                """
            ),
            {"id": payload.targetId},
        ).mappings().first()
        if target is None:
            raise HTTPException(status_code=400, detail="unknown target")
        if target["project_status"] != "ACTIVE":
            raise HTTPException(status_code=409, detail="project is archived")
        connection.execute(
            text(
                """
                INSERT INTO scan_job
                    (id, project_id, target_id, name, profile_id, status, created_at, updated_at, created_by)
                VALUES (:id, :project_id, :target_id, :name, :profile_id, 'QUEUED', :created_at, :created_at, 'user-maya')
                """
            ),
            {
                "id": scan_id,
                "project_id": target["project_id"],
                "target_id": payload.targetId,
                "name": payload.name.strip(),
                "profile_id": profile_id,
                "created_at": now,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "scan_job.queued",
            "SCAN_JOB",
            scan_id,
            payload.name.strip(),
            outcome="SIMULATED",
            metadata={"projectId": target["project_id"], "targetId": payload.targetId},
        )
    return {
        "id": scan_id,
        "projectId": target["project_id"],
        "targetId": payload.targetId,
        "name": payload.name.strip(),
        "profile": payload.profile,
        "status": "Queued",
        "progress": 0,
        "simulated": True,
        "createdAt": now.isoformat(),
        "completedAt": None,
    }


@app.post("/api/v1/scans/{scan_id}/run")
def run_simulated_scan(scan_id: str, request: Request) -> dict:
    now = datetime.now(timezone.utc)
    finding_id = f"finding-{uuid4().hex[:12]}"
    evidence_id = f"evidence-{uuid4().hex[:12]}"
    event_id = f"fse-{uuid4().hex[:12]}"
    run_id = f"run-{uuid4().hex[:12]}"
    with get_engine().begin() as connection:
        job = connection.execute(
            text(
                """
                SELECT j.id, j.project_id, j.target_id, j.name, j.status,
                       t.name AS target_name, t.scope AS target_scope
                FROM scan_job j JOIN target t ON t.id = j.target_id
                WHERE j.id = :id
                """
            ),
            {"id": scan_id},
        ).mappings().first()
        if job is None:
            raise HTTPException(status_code=404, detail="scan not found")
        if job["status"] not in {"QUEUED", "FAILED", "RUNNING"}:
            raise HTTPException(
                status_code=409, detail="Only queued, failed, or claimed scans can run."
            )
        pending = connection.execute(
            text(
                """
                SELECT id, attempt FROM scan_run
                WHERE job_id = :id AND status = 'PENDING'
                ORDER BY attempt DESC
                FOR UPDATE
                LIMIT 1
                """
            ),
            {"id": scan_id},
        ).mappings().first()
        if pending is not None:
            run_id = pending["id"]
            attempt = pending["attempt"]
        else:
            attempt = connection.execute(
                text("SELECT COALESCE(MAX(attempt), 0) + 1 FROM scan_run WHERE job_id = :id"),
                {"id": scan_id},
            ).scalar_one()
        adapter = build_scanner()
        result = adapter.scan(
            ScanJobContext(
                job_id=job["id"],
                project_id=job["project_id"],
                target_id=job["target_id"],
                target_name=job["target_name"],
                target_scope=job["target_scope"] or "",
            )
        )
        if len(result.findings) != 1:
            raise HTTPException(status_code=500, detail="demo adapter returned an invalid result")
        finding_spec = result.findings[0]
        connection.execute(
            text("UPDATE scan_job SET status = 'COMPLETED', updated_at = :now WHERE id = :id"),
            {"id": scan_id, "now": now},
        )
        if pending is not None:
            connection.execute(
                text(
                    """
                    UPDATE scan_run
                    SET status = 'SUCCEEDED', progress = 100, adapter_code = :adapter_code,
                        started_at = :now, finished_at = :now, heartbeat_at = :now,
                        stats = CAST(:stats AS jsonb), error_message = NULL
                    WHERE id = :id
                    """
                ),
                {
                    "id": run_id,
                    "adapter_code": result.adapter_code,
                    "now": now,
                    "stats": '{"simulated": true}',
                },
            )
        else:
            connection.execute(
                text(
                    """
                    INSERT INTO scan_run
                        (id, job_id, attempt, status, progress, adapter_code, worker_id,
                         started_at, finished_at, heartbeat_at, stats, created_at)
                    VALUES (:id, :job_id, :attempt, 'SUCCEEDED', 100, :adapter_code, 'worker-1',
                            :now, :now, :now, CAST(:stats AS jsonb), :now)
                    """
                ),
                {
                    "id": run_id,
                    "job_id": scan_id,
                    "attempt": attempt,
                    "adapter_code": result.adapter_code,
                    "now": now,
                    "stats": '{"simulated": true}',
                },
            )
        connection.execute(
            text(
                """
                INSERT INTO finding
                    (id, project_id, target_id, job_id, run_id, dedup_key, title, severity,
                     status, notes, source, created_at, created_by, updated_at)
                VALUES (:id, :project_id, :target_id, :job_id, :run_id, :dedup_key,
                        :title, :severity, :status, :notes, 'DEMO', :now, 'user-maya', :now)
                """
            ),
            {
                "id": finding_id,
                "project_id": job["project_id"],
                "target_id": job["target_id"],
                "job_id": scan_id,
                "run_id": run_id,
                "dedup_key": f"sim-{finding_id}",
                "title": finding_spec.title,
                "severity": finding_spec.severity,
                "status": finding_spec.status,
                "notes": finding_spec.notes,
                "now": now,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO evidence
                    (id, finding_id, run_id, kind, title, content, sha256, mime_type,
                     captured_at, created_at, created_by)
                VALUES (:id, :finding_id, :run_id, 'TEXT', 'Demo evidence', :content,
                        :sha256, 'text/plain', :now, :now, 'user-maya')
                """
            ),
            {
                "id": evidence_id,
                "finding_id": finding_id,
                "run_id": run_id,
                "content": finding_spec.evidence,
                "sha256": hashlib.sha256(finding_spec.evidence.encode()).hexdigest(),
                "now": now,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO finding_status_event
                    (id, finding_id, from_status, to_status, actor_id, reason, occurred_at)
                VALUES (:id, :finding_id, NULL, :to_status, 'user-maya',
                        'Created by simulated scan.', :now)
                """
            ),
            {
                "id": event_id,
                "finding_id": finding_id,
                "to_status": finding_spec.status,
                "now": now,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "scan_job.completed",
            "SCAN_JOB",
            scan_id,
            job["name"],
            outcome="SIMULATED",
            metadata={
                "findingId": finding_id,
                "projectId": job["project_id"],
                "targetId": job["target_id"],
            },
        )
    return {
        "scan": {
            "id": scan_id,
            "status": "Completed",
            "progress": 100,
            "completedAt": now.isoformat(),
        },
        "finding": {
            "id": finding_id,
            "title": finding_spec.title,
            "severity": SEVERITY_LABEL[finding_spec.severity],
            "status": STATUS_LABEL[finding_spec.status],
            "projectId": job["project_id"],
            "targetId": job["target_id"],
            "scanId": scan_id,
            "createdAt": now.isoformat(),
        },
    }


@app.patch("/api/v1/findings/{finding_id}/status")
def update_finding_status(finding_id: str, payload: FindingStatusInput) -> dict:
    now = datetime.now(timezone.utc)
    event_id = f"fse-{uuid4().hex[:12]}"
    with get_engine().begin() as connection:
        current = connection.execute(
            text("SELECT id, status FROM finding WHERE id = :id"),
            {"id": finding_id},
        ).mappings().first()
        if current is None:
            raise HTTPException(status_code=404, detail="finding not found")
        connection.execute(
            text(
                """
                UPDATE finding
                SET status = CAST(:status AS finding_status),
                    updated_at = :now,
                    resolved_at = COALESCE(:resolved_at, resolved_at)
                WHERE id = :id
                """
            ),
            {
                "id": finding_id,
                "status": payload.status,
                "now": now,
                "resolved_at": now if payload.status == "RESOLVED" else None,
            },
        )
        if current["status"] != payload.status:
            connection.execute(
                text(
                    """
                    INSERT INTO finding_status_event
                        (id, finding_id, from_status, to_status, actor_id, reason, occurred_at)
                    VALUES (:id, :finding_id, :from_status, :to_status, 'user-maya',
                            'Analyst status transition.', :occurred_at)
                    """
                ),
                {
                    "id": event_id,
                    "finding_id": finding_id,
                    "from_status": current["status"],
                    "to_status": payload.status,
                    "occurred_at": now,
                },
            )
    return {
        "id": finding_id,
        "status": {
            "NEW": "New",
            "CONFIRMED": "Confirmed",
            "IN_PROGRESS": "In Progress",
            "RESOLVED": "Resolved",
            "REOPENED": "Reopened",
            "ACCEPTED_RISK": "Accepted Risk",
            "FALSE_POSITIVE": "False Positive",
        }[payload.status],
    }


def _call_ai(title: str, severity: str) -> dict | None:
    url = os.getenv(
        "SENTRIX_AI_URL", "http://10.20.10.30:8001/v1/analyze"
    )
    request = urllib.request.Request(
        url,
        data=json.dumps({"title": title, "severity": severity}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.load(response)
    except Exception as exc:  # fall back to deterministic local output
        print(f"AI call failed: {exc}", flush=True)
        return None


@app.post("/api/v1/findings/{finding_id}/transitions")
def transition_finding(
    finding_id: str, payload: TransitionInput, request: Request
) -> dict:
    if payload.to == "RESOLVED":
        raise HTTPException(
            status_code=409,
            detail="A finding can only be resolved by a recorded verification.",
        )
    reason = (payload.reason or "").strip()
    if len(reason) > 1000:
        raise HTTPException(status_code=422, detail="reason is too long")
    now = datetime.now(timezone.utc)
    event_id = f"fse-{uuid4().hex[:12]}"
    audit_id = f"audit-{uuid4().hex[:12]}"
    user_id = request.state.user["sub"]
    with get_engine().begin() as connection:
        finding = connection.execute(
            text(
                "SELECT id, status, title FROM finding WHERE id = :id FOR UPDATE"
            ),
            {"id": finding_id},
        ).mappings().first()
        if finding is None:
            raise HTTPException(status_code=404, detail="finding not found")
        current = finding["status"]
        if current == payload.to:
            raise HTTPException(
                status_code=409,
                detail=f"Finding cannot move from {STATUS_LABEL[current]} to {STATUS_LABEL[payload.to]}.",
            )
        if payload.to not in TRANSITIONS.get(current, set()):
            raise HTTPException(
                status_code=409,
                detail=f"Finding cannot move from {STATUS_LABEL[current]} to {STATUS_LABEL[payload.to]}.",
            )
        if (current, payload.to) in REASON_REQUIRED and not reason:
            raise HTTPException(status_code=422, detail="reason is required")
        connection.execute(
            text(
                """
                UPDATE finding
                SET status = CAST(:status AS finding_status),
                    updated_at = :now,
                    resolved_at = CASE WHEN CAST(:status AS text) = 'REOPENED'
                                       THEN NULL ELSE resolved_at END
                WHERE id = :id
                """
            ),
            {"id": finding_id, "status": payload.to, "now": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO finding_status_event
                    (id, finding_id, from_status, to_status, actor_id, reason, occurred_at)
                VALUES (:id, :finding_id, :from_status, :to_status, :actor_id,
                        :reason, :occurred_at)
                """
            ),
            {
                "id": event_id,
                "finding_id": finding_id,
                "from_status": current,
                "to_status": payload.to,
                "actor_id": user_id,
                "reason": reason or "Analyst transition.",
                "occurred_at": now,
            },
        )
        actor = connection.execute(
            text("SELECT display_name FROM app_user WHERE id = :id"),
            {"id": user_id},
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO audit_event
                    (id, occurred_at, actor_id, actor_label, action, resource_type,
                     resource_id, resource_name, outcome, request_id, metadata)
                VALUES (:id, :now, :actor_id, :actor_label, 'finding.transitioned',
                        'FINDING', :resource_id, :resource_name, 'SUCCESS', 'api',
                        CAST(:metadata AS jsonb))
                """
            ),
            {
                "id": audit_id,
                "now": now,
                "actor_id": user_id,
                "actor_label": actor,
                "resource_id": finding_id,
                "resource_name": finding["title"],
                "metadata": json.dumps(
                    {"from": current, "to": payload.to, "reason": reason}
                ),
            },
        )
    return {
        "id": finding_id,
        "from": STATUS_LABEL[current],
        "status": STATUS_LABEL[payload.to],
    }


@app.post("/api/v1/findings/{finding_id}/analyses", status_code=201)
def create_analysis(finding_id: str, request: Request) -> dict:
    now = datetime.now(timezone.utc)
    analysis_id = f"analysis-{uuid4().hex[:12]}"
    with get_engine().begin() as connection:
        finding = connection.execute(
            text("SELECT id, title, severity FROM finding WHERE id = :id"),
            {"id": finding_id},
        ).mappings().first()
        if finding is None:
            raise HTTPException(status_code=404, detail="finding not found")
        inference = build_inference().analyze(
            InferenceContext(
                finding_id=finding_id,
                title=finding["title"],
                severity=finding["severity"],
            )
        )
        summary = inference.summary
        limitations = inference.limitations
        confidence = inference.confidence
        model = inference.model
        version = inference.version
        input_hash = inference.input_hash
        latency_ms = inference.latency_ms
        connection.execute(
            text(
                """
                INSERT INTO analysis
                    (id, finding_id, model_version_id, prompt_template_version_id,
                     status, confidence, summary, limitations, input_hash, latency_ms,
                     simulated, created_at, completed_at)
                VALUES (:id, :finding_id, 'modelversion-risk-4.8.2', 'ptv-risk-1',
                        'COMPLETED', :confidence, :summary, :limitations, :input_hash,
                        :latency_ms, TRUE, :now, :now)
                """
            ),
            {
                "id": analysis_id,
                "finding_id": finding_id,
                "summary": summary,
                "limitations": limitations,
                "confidence": confidence,
                "input_hash": input_hash,
                "latency_ms": latency_ms,
                "now": now,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "analysis.completed",
            "FINDING",
            finding_id,
            finding["title"],
            outcome="SIMULATED",
            metadata={"analysisId": analysis_id, "model": model, "version": version},
        )
    return {
        "id": analysis_id,
        "findingId": finding_id,
        "model": model,
        "version": version,
        "status": "Completed",
        "confidence": round(confidence * 100),
        "summary": summary,
        "limitations": limitations,
        "createdAt": now.isoformat(),
        "simulated": True,
    }


@app.post("/api/v1/findings/{finding_id}/remediations", status_code=201)
def create_remediation(finding_id: str, payload: RemediationInput, request: Request) -> dict:
    now = datetime.now(timezone.utc)
    remediation_id = f"task-{uuid4().hex[:12]}"
    due = date.fromisoformat(payload.dueDate) if payload.dueDate else None
    with get_engine().begin() as connection:
        finding = connection.execute(
            text("SELECT id FROM finding WHERE id = :id"),
            {"id": finding_id},
        ).first()
        if finding is None:
            raise HTTPException(status_code=404, detail="finding not found")
        connection.execute(
            text(
                """
                INSERT INTO remediation
                    (id, finding_id, assignee_id, due_date, status, notes,
                     created_at, updated_at, created_by)
                VALUES (:id, :finding_id, 'user-maya', :due_date, 'IN_PROGRESS',
                        :notes, :now, :now, 'user-maya')
                """
            ),
            {
                "id": remediation_id,
                "finding_id": finding_id,
                "due_date": due,
                "notes": payload.notes or "Demo remediation task",
                "now": now,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "remediation.created",
            "REMEDIATION",
            remediation_id,
            finding_id,
            metadata={"findingId": finding_id, "dueDate": due.isoformat() if due else None},
        )
    return {
        "id": remediation_id,
        "findingId": finding_id,
        "assignee": "Maya Chen",
        "dueDate": due.isoformat() if due else "",
        "status": "In Progress",
        "notes": payload.notes or "Demo remediation task",
        "verification": None,
    }


@app.post("/api/v1/remediations/{remediation_id}/verify")
def verify_remediation(
    remediation_id: str, payload: VerificationInput, request: Request
) -> dict:
    now = datetime.now(timezone.utc)
    verification_id = f"verification-{uuid4().hex[:12]}"
    event_id = f"fse-{uuid4().hex[:12]}"
    new_finding_status = "RESOLVED" if payload.outcome == "VERIFIED" else "REOPENED"
    new_task_status = "COMPLETED" if payload.outcome == "VERIFIED" else "REOPENED"
    with get_engine().begin() as connection:
        task = connection.execute(
            text(
                """
                SELECT r.id, r.finding_id, f.status AS finding_status
                FROM remediation r JOIN finding f ON f.id = r.finding_id
                WHERE r.id = :id
                """
            ),
            {"id": remediation_id},
        ).mappings().first()
        if task is None:
            raise HTTPException(status_code=404, detail="remediation not found")
        allowed_states = (
            {"IN_PROGRESS", "REOPENED"}
            if payload.outcome == "VERIFIED"
            else {"IN_PROGRESS", "RESOLVED", "REOPENED"}
        )
        if task["finding_status"] not in allowed_states:
            raise HTTPException(
                status_code=409,
                detail="Finding state does not allow this verification.",
            )
        connection.execute(
            text(
                """
                INSERT INTO verification
                    (id, finding_id, remediation_id, outcome, method, verifier_id,
                     evidence_id, notes, verified_at, created_at)
                VALUES (:id, :finding_id, :remediation_id, :outcome, :method,
                        'user-maya', NULL, :notes, :now, :now)
                """
            ),
            {
                "id": verification_id,
                "finding_id": task["finding_id"],
                "remediation_id": remediation_id,
                "outcome": payload.outcome,
                "method": payload.method,
                "notes": payload.notes or "Demo verification.",
                "now": now,
            },
        )
        connection.execute(
            text(
                """
                UPDATE remediation
                SET status = CAST(:status AS remediation_status),
                    updated_at = :now,
                    closed_at = COALESCE(:closed_at, closed_at)
                WHERE id = :id
                """
            ),
            {
                "id": remediation_id,
                "status": new_task_status,
                "now": now,
                "closed_at": now if new_task_status == "COMPLETED" else None,
            },
        )
        connection.execute(
            text(
                """
                UPDATE finding
                SET status = CAST(:status AS finding_status),
                    updated_at = :now,
                    resolved_at = COALESCE(:resolved_at, resolved_at)
                WHERE id = :finding_id
                """
            ),
            {
                "finding_id": task["finding_id"],
                "status": new_finding_status,
                "now": now,
                "resolved_at": now if new_finding_status == "RESOLVED" else None,
            },
        )
        if task["finding_status"] != new_finding_status:
            connection.execute(
                text(
                    """
                    INSERT INTO finding_status_event
                        (id, finding_id, from_status, to_status, actor_id, reason, occurred_at)
                    VALUES (:id, :finding_id, :from_status, :to_status, 'user-maya',
                            'Remediation verification.', :occurred_at)
                    """
                ),
                {
                    "id": event_id,
                    "finding_id": task["finding_id"],
                    "from_status": task["finding_status"],
                    "to_status": new_finding_status,
                    "occurred_at": now,
                },
            )
        _audit(
            connection,
            request.state.user["sub"],
            "verification.recorded",
            "FINDING",
            task["finding_id"],
            task["finding_id"],
            metadata={
                "remediationId": remediation_id,
                "outcome": payload.outcome,
                "method": payload.method,
                "from": task["finding_status"],
                "to": new_finding_status,
            },
        )
    return {
        "id": remediation_id,
        "findingId": task["finding_id"],
        "status": "Completed" if payload.outcome == "VERIFIED" else "Reopened",
        "verification": payload.outcome,
        "findingStatus": "Resolved" if payload.outcome == "VERIFIED" else "Reopened",
    }


@app.post("/api/v1/reports", status_code=201)
def create_report(payload: ReportInput, request: Request) -> dict:
    now = datetime.now(timezone.utc)
    report_id = f"report-{uuid4().hex[:12]}"
    with get_engine().begin() as connection:
        project = connection.execute(
            text("SELECT id FROM project WHERE id = :id"),
            {"id": payload.projectId},
        ).first()
        if project is None:
            raise HTTPException(status_code=400, detail="unknown project")
        connection.execute(
            text(
                """
                INSERT INTO report
                    (id, project_id, job_id, title, status, snapshot_hash,
                     created_at, created_by)
                VALUES (:id, :project_id, :job_id, :title, 'DRAFT', :snapshot_hash,
                        :now, 'user-maya')
                """
            ),
            {
                "id": report_id,
                "project_id": payload.projectId,
                "job_id": payload.scanId,
                "title": payload.title.strip(),
                "snapshot_hash": hashlib.sha256(
                    f"{payload.projectId}:{payload.title}".encode()
                ).hexdigest(),
                "now": now,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "report.created",
            "REPORT",
            report_id,
            payload.title.strip(),
            metadata={"projectId": payload.projectId, "scanId": payload.scanId},
        )
    return {
        "id": report_id,
        "projectId": payload.projectId,
        "scanId": payload.scanId,
        "title": payload.title.strip(),
        "status": "Draft",
        "createdAt": now.isoformat(),
    }


@app.post("/api/v1/reports/{report_id}/publish")
def publish_report(report_id: str, request: Request) -> dict:
    now = datetime.now(timezone.utc)
    with get_engine().begin() as connection:
        report = connection.execute(
            text("SELECT id, title, project_id FROM report WHERE id = :id"),
            {"id": report_id},
        ).mappings().first()
        if report is None:
            raise HTTPException(status_code=404, detail="report not found")
        connection.execute(
            text(
                "UPDATE report SET status = 'PUBLISHED', published_at = :now WHERE id = :id"
            ),
            {"id": report_id, "now": now},
        )
        _audit(
            connection,
            request.state.user["sub"],
            "report.published",
            "REPORT",
            report_id,
            report["title"],
            metadata={"projectId": report["project_id"]},
        )
    return {"id": report_id, "status": "Published", "publishedAt": now.isoformat()}


@app.get("/api/v1/projects/{project_id}/members")
def list_members(project_id: str) -> list[dict]:
    with get_engine().connect() as connection:
        project = connection.execute(
            text("SELECT id FROM project WHERE id = :id"), {"id": project_id}
        ).first()
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        rows = connection.execute(
            text(
                """
                SELECT m.user_id, u.display_name, m.role, m.created_at
                FROM project_member m JOIN app_user u ON u.id = m.user_id
                WHERE m.project_id = :project_id
                ORDER BY m.created_at, m.user_id
                """
            ),
            {"project_id": project_id},
        ).mappings().all()
    return [
        {
            "userId": row["user_id"],
            "displayName": row["display_name"],
            "role": row["role"],
            "createdAt": row["created_at"].isoformat(),
        }
        for row in rows
    ]


@app.post("/api/v1/projects/{project_id}/members", status_code=201)
def add_member(project_id: str, payload: MembershipInput, request: Request) -> dict:
    now = datetime.now(timezone.utc)
    with get_engine().begin() as connection:
        _require_project_owner(connection, project_id, request)
        user = connection.execute(
            text("SELECT id, display_name, is_active FROM app_user WHERE id = :id"),
            {"id": payload.userId},
        ).mappings().first()
        if user is None or not user["is_active"]:
            raise HTTPException(status_code=422, detail="unknown or inactive user")
        existing = connection.execute(
            text(
                "SELECT 1 FROM project_member WHERE project_id = :project_id AND user_id = :user_id"
            ),
            {"project_id": project_id, "user_id": payload.userId},
        ).first()
        if existing is not None:
            raise HTTPException(status_code=409, detail="This user is already a member of the project.")
        connection.execute(
            text(
                """
                INSERT INTO project_member (project_id, user_id, role, created_at)
                VALUES (:project_id, :user_id, :role, :now)
                """
            ),
            {
                "project_id": project_id,
                "user_id": payload.userId,
                "role": payload.role,
                "now": now,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "membership.granted",
            "PROJECT",
            project_id,
            project_id,
            metadata={"userId": payload.userId, "role": payload.role},
        )
    return {
        "projectId": project_id,
        "userId": payload.userId,
        "displayName": user["display_name"],
        "role": payload.role,
    }


@app.patch("/api/v1/projects/{project_id}/members/{user_id}")
def change_member_role(
    project_id: str, user_id: str, payload: MembershipRoleInput, request: Request
) -> dict:
    with get_engine().begin() as connection:
        _require_project_owner(connection, project_id, request)
        member = connection.execute(
            text(
                "SELECT role FROM project_member WHERE project_id = :project_id AND user_id = :user_id"
            ),
            {"project_id": project_id, "user_id": user_id},
        ).first()
        if member is None:
            raise HTTPException(status_code=404, detail="membership not found")
        if member[0] == "OWNER" and payload.role != "OWNER":
            owners = connection.execute(
                text(
                    "SELECT count(*) FROM project_member WHERE project_id = :project_id AND role = 'OWNER'"
                ),
                {"project_id": project_id},
            ).scalar_one()
            if owners <= 1:
                raise HTTPException(status_code=409, detail="A project must keep at least one owner.")
        connection.execute(
            text(
                "UPDATE project_member SET role = :role WHERE project_id = :project_id AND user_id = :user_id"
            ),
            {"project_id": project_id, "user_id": user_id, "role": payload.role},
        )
        _audit(
            connection,
            request.state.user["sub"],
            "membership.updated",
            "PROJECT",
            project_id,
            project_id,
            metadata={"userId": user_id, "role": payload.role},
        )
    return {"projectId": project_id, "userId": user_id, "role": payload.role}


@app.delete("/api/v1/projects/{project_id}/members/{user_id}", status_code=204)
def remove_member(project_id: str, user_id: str, request: Request) -> Response:
    with get_engine().begin() as connection:
        _require_project_owner(connection, project_id, request)
        member = connection.execute(
            text(
                "SELECT role FROM project_member WHERE project_id = :project_id AND user_id = :user_id"
            ),
            {"project_id": project_id, "user_id": user_id},
        ).first()
        if member is None:
            raise HTTPException(status_code=404, detail="membership not found")
        if member[0] == "OWNER":
            owners = connection.execute(
                text(
                    "SELECT count(*) FROM project_member WHERE project_id = :project_id AND role = 'OWNER'"
                ),
                {"project_id": project_id},
            ).scalar_one()
            if owners <= 1:
                raise HTTPException(status_code=409, detail="A project must keep at least one owner.")
        connection.execute(
            text(
                "DELETE FROM project_member WHERE project_id = :project_id AND user_id = :user_id"
            ),
            {"project_id": project_id, "user_id": user_id},
        )
        _audit(
            connection,
            request.state.user["sub"],
            "membership.removed",
            "PROJECT",
            project_id,
            project_id,
            metadata={"userId": user_id},
        )
    return Response(status_code=204)


@app.post("/api/v1/users", status_code=201)
def provision_user(payload: UserInput, request: Request) -> dict:
    _require_admin(request)
    now = datetime.now(timezone.utc)
    user_id = f"user-{uuid4().hex[:12]}"
    with get_engine().begin() as connection:
        duplicate = connection.execute(
            text("SELECT 1 FROM app_user WHERE lower(email) = lower(:email)"),
            {"email": payload.email.strip()},
        ).first()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="email already exists")
        connection.execute(
            text(
                """
                INSERT INTO app_user
                    (id, display_name, email, role, password_hash, is_active, created_at)
                VALUES (:id, :display_name, :email, :role, :password_hash, TRUE, :now)
                """
            ),
            {
                "id": user_id,
                "display_name": payload.displayName.strip(),
                "email": payload.email.strip(),
                "role": payload.role,
                "password_hash": hash_password(payload.password),
                "now": now,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "user.created",
            "USER",
            user_id,
            payload.displayName.strip(),
            metadata={"role": payload.role, "email": payload.email.strip()},
        )
    return {
        "id": user_id,
        "displayName": payload.displayName.strip(),
        "email": payload.email.strip(),
        "role": payload.role,
        "isActive": True,
    }


@app.patch("/api/v1/users/{user_id}")
def update_user(user_id: str, payload: UserPatch, request: Request) -> dict:
    _require_admin(request)
    with get_engine().begin() as connection:
        user = connection.execute(
            text("SELECT id, display_name, role, is_active FROM app_user WHERE id = :id"),
            {"id": user_id},
        ).mappings().first()
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        new_role = payload.role or user["role"]
        new_active = user["is_active"] if payload.isActive is None else payload.isActive
        if user["role"] == "ADMIN" and (new_role != "ADMIN" or not new_active):
            admins = connection.execute(
                text("SELECT count(*) FROM app_user WHERE role = 'ADMIN' AND is_active = TRUE")
            ).scalar_one()
            if admins <= 1:
                raise HTTPException(status_code=409, detail="At least one active admin is required.")
        connection.execute(
            text(
                """
                UPDATE app_user
                SET display_name = COALESCE(:display_name, display_name),
                    role = :role,
                    is_active = :is_active
                WHERE id = :id
                """
            ),
            {
                "id": user_id,
                "display_name": payload.displayName.strip() if payload.displayName else None,
                "role": new_role,
                "is_active": new_active,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "user.updated",
            "USER",
            user_id,
            payload.displayName.strip() if payload.displayName else user["display_name"],
            metadata={"role": new_role, "isActive": new_active},
        )
    return {
        "id": user_id,
        "displayName": payload.displayName or user["display_name"],
        "role": new_role,
        "isActive": new_active,
    }


@app.post("/api/v1/worker/claims")
def claim_scan(request: Request):
    now = datetime.now(timezone.utc)
    with get_engine().begin() as connection:
        job = connection.execute(
            text(
                """
                SELECT j.id, j.project_id, j.target_id, j.name, j.status,
                       t.name AS target_name
                FROM scan_job j JOIN target t ON t.id = j.target_id
                WHERE j.status IN ('QUEUED', 'FAILED')
                  AND NOT EXISTS (
                      SELECT 1 FROM scan_run r
                      WHERE r.job_id = j.id AND r.status IN ('PENDING', 'RUNNING')
                  )
                ORDER BY j.created_at, j.id
                FOR UPDATE OF j SKIP LOCKED
                LIMIT 1
                """
            )
        ).mappings().first()
        if job is None:
            return Response(status_code=204)
        attempt = connection.execute(
            text("SELECT COALESCE(MAX(attempt), 0) + 1 FROM scan_run WHERE job_id = :id"),
            {"id": job["id"]},
        ).scalar_one()
        run_id = f"run-{uuid4().hex[:12]}"
        connection.execute(
            text(
                """
                INSERT INTO scan_run
                    (id, job_id, attempt, status, progress, adapter_code, worker_id,
                     heartbeat_at, created_at)
                VALUES (:id, :job_id, :attempt, 'PENDING', 0, 'demo', 'worker-1',
                        :now, :now)
                """
            ),
            {"id": run_id, "job_id": job["id"], "attempt": attempt, "now": now},
        )
        connection.execute(
            text("UPDATE scan_job SET status = 'RUNNING', updated_at = :now WHERE id = :id"),
            {"id": job["id"], "now": now},
        )
        _audit(
            connection,
            request.state.user["sub"],
            "scan_job.running",
            "SCAN_JOB",
            job["id"],
            job["name"],
            outcome="SIMULATED",
            metadata={"runId": run_id, "attempt": attempt},
        )
    return {
        "job": {
            "id": job["id"],
            "projectId": job["project_id"],
            "targetId": job["target_id"],
            "name": job["name"],
            "status": "Running",
        },
        "runId": run_id,
        "attempt": attempt,
    }


@app.post("/api/v1/worker/claims/{run_id}/heartbeat")
def heartbeat_claim(run_id: str) -> dict:
    now = datetime.now(timezone.utc)
    with get_engine().begin() as connection:
        updated = connection.execute(
            text(
                """
                UPDATE scan_run SET heartbeat_at = :now
                WHERE id = :id AND status IN ('PENDING', 'RUNNING')
                """
            ),
            {"id": run_id, "now": now},
        ).rowcount
    if not updated:
        raise HTTPException(status_code=404, detail="active run not found")
    return {"runId": run_id, "heartbeatAt": now.isoformat()}


@app.post("/api/v1/worker/recover")
def recover_stale_runs() -> dict:
    now = datetime.now(timezone.utc)
    recovered: list[str] = []
    with get_engine().begin() as connection:
        stale = connection.execute(
            text(
                """
                SELECT id, job_id FROM scan_run
                WHERE status IN ('PENDING', 'RUNNING')
                  AND worker_id = 'worker-1'
                  AND COALESCE(heartbeat_at, created_at) < :cutoff
                FOR UPDATE SKIP LOCKED
                """
            ),
            {"cutoff": now - timedelta(minutes=5)},
        ).mappings().all()
        for run in stale:
            connection.execute(
                text(
                    """
                    UPDATE scan_run
                    SET status = 'FAILED', finished_at = :now,
                        error_message = 'stale heartbeat'
                    WHERE id = :id
                    """
                ),
                {"id": run["id"], "now": now},
            )
            connection.execute(
                text(
                    """
                    UPDATE scan_job
                    SET status = 'FAILED', failure_reason = 'stale heartbeat',
                        updated_at = :now
                    WHERE id = :job_id
                    """
                ),
                {"job_id": run["job_id"], "now": now},
            )
            recovered.append(run["id"])
    return {"recovered": recovered}


@app.post("/api/v1/artifacts", status_code=201)
async def register_artifact(request: Request) -> dict:
    project_id = request.headers.get("X-Project-Id", "").strip()
    evidence_id = request.headers.get("X-Evidence-Id", "").strip() or None
    if not project_id:
        raise HTTPException(status_code=422, detail="X-Project-Id is required")
    payload = await request.body()
    if not payload:
        raise HTTPException(status_code=422, detail="artifact body is required")
    if len(payload) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="artifact exceeds the configured size limit")

    with get_engine().begin() as connection:
        project = connection.execute(
            text("SELECT id, status FROM project WHERE id = :id"),
            {"id": project_id},
        ).mappings().first()
        if project is None:
            raise HTTPException(status_code=404, detail="project not found")
        if project["status"] != "ACTIVE":
            raise HTTPException(status_code=409, detail="project is not active")
        _require_project_member(
            connection, project_id, request, roles={"OWNER", "ANALYST"}
        )
        if evidence_id:
            evidence_project = connection.execute(
                text(
                    """
                    SELECT f.project_id FROM evidence e
                    JOIN finding f ON f.id = e.finding_id
                    WHERE e.id = :id
                    """
                ),
                {"id": evidence_id},
            ).scalar_one_or_none()
            if evidence_project != project_id:
                raise HTTPException(status_code=422, detail="evidence belongs to another project")
        try:
            key = build_artifact_store().put(payload)
        except ArtifactStoreError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        connection.execute(
            text(
                """
                INSERT INTO artifact (sha256, project_id, evidence_id, created_by, created_at)
                VALUES (:sha256, :project_id, :evidence_id, :created_by, :now)
                ON CONFLICT (sha256) DO NOTHING
                """
            ),
            {
                "sha256": key,
                "project_id": project_id,
                "evidence_id": evidence_id,
                "created_by": request.state.user["sub"],
                "now": datetime.now(timezone.utc),
            },
        )
        stored = connection.execute(
            text("SELECT project_id, evidence_id FROM artifact WHERE sha256 = :sha256"),
            {"sha256": key},
        ).mappings().first()
        if stored["project_id"] != project_id:
            raise HTTPException(status_code=409, detail="artifact belongs to another project")
        _audit(
            connection,
            request.state.user["sub"],
            "artifact.registered",
            "ARTIFACT",
            key,
            key,
            metadata={"projectId": project_id, "evidenceId": evidence_id, "size": len(payload)},
        )
    return {
        "sha256": key,
        "projectId": project_id,
        "evidenceId": evidence_id,
        "size": len(payload),
    }


@app.get("/api/v1/artifacts/{key}")
def download_artifact(key: str, request: Request) -> Response:
    with get_engine().connect() as connection:
        artifact = connection.execute(
            text("SELECT sha256, project_id FROM artifact WHERE sha256 = :sha256"),
            {"sha256": key},
        ).mappings().first()
        if artifact is None:
            raise HTTPException(status_code=404, detail="artifact not found")
        _require_project_member(connection, artifact["project_id"], request)
    try:
        payload = build_artifact_store().get(key)
    except ArtifactStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{key}.bin"',
            "X-Content-Type-Options": "nosniff",
            "Content-Length": str(len(payload)),
        },
    )


@app.get("/api/v1/evaluations")
def evaluations() -> dict:
    with get_engine().connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT e.id, e.model_version_id, e.dataset_version_id, e.status,
                       e.data_origin, e.metrics, e.environment, e.seed,
                       e.started_at, e.finished_at,
                       m.name AS model_name, mv.version AS model_version,
                       d.name AS dataset_name, dv.version AS dataset_version
                FROM evaluation_run e
                JOIN model_version mv ON mv.id = e.model_version_id
                JOIN model m ON m.id = mv.model_id
                JOIN dataset_version dv ON dv.id = e.dataset_version_id
                JOIN dataset d ON d.id = dv.dataset_id
                ORDER BY e.started_at DESC, e.id
                """
            )
        ).mappings().all()
    return {
        "evaluations": [
            {
                "id": row["id"],
                "modelVersionId": row["model_version_id"],
                "model": row["model_name"],
                "modelVersion": row["model_version"],
                "datasetVersionId": row["dataset_version_id"],
                "dataset": row["dataset_name"],
                "datasetVersion": row["dataset_version"],
                "status": row["status"],
                "dataOrigin": row["data_origin"],
                "metrics": row["metrics"],
                "environment": row["environment"],
                "seed": row["seed"],
                "startedAt": row["started_at"].isoformat(),
                "finishedAt": row["finished_at"].isoformat() if row["finished_at"] else None,
            }
            for row in rows
        ],
    }


@app.get("/api/v1/automation/actions")
def automation_actions(request: Request) -> dict:
    _require_admin(request)
    return {
        "actions": [
            {
                "code": spec.code,
                "actionClass": spec.action_class,
                "tier": int(spec.tier),
                "description": spec.description,
            }
            for spec in CATALOG.values()
        ]
    }


@app.post("/api/v1/automation/candidates", status_code=201)
def create_automation_candidate(payload: AutomationCandidateInput, request: Request) -> dict:
    _require_admin(request)
    candidate_id = f"candidate-{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    with get_engine().begin() as connection:
        finding = connection.execute(
            text("SELECT id FROM finding WHERE id = :id"), {"id": payload.findingId}
        ).first()
        if finding is None:
            raise HTTPException(status_code=404, detail="finding not found")
        connection.execute(
            text(
                """
                INSERT INTO automation_candidate
                    (id, finding_id, target, action_code, score, status, created_by, created_at, updated_at)
                VALUES (:id, :finding_id, :target, :action_code, :score, 'QUEUED', :created_by, :now, :now)
                """
            ),
            {
                "id": candidate_id,
                "finding_id": payload.findingId,
                "target": payload.target.strip(),
                "action_code": payload.actionCode,
                "score": max(0.0, min(1.0, payload.score)),
                "created_by": request.state.user["sub"],
                "now": now,
            },
        )
        _audit(
            connection,
            request.state.user["sub"],
            "automation.candidate_created",
            "AUTOMATION_CANDIDATE",
            candidate_id,
            payload.target,
            metadata={"findingId": payload.findingId, "actionCode": payload.actionCode},
        )
    return {
        "id": candidate_id,
        "findingId": payload.findingId,
        "target": payload.target.strip(),
        "actionCode": payload.actionCode,
        "score": payload.score,
        "status": "QUEUED",
    }


@app.get("/api/v1/automation/candidates")
def automation_candidates(request: Request) -> dict:
    _require_admin(request)
    with get_engine().connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, finding_id, target, action_code, score, status, created_at
                FROM automation_candidate ORDER BY score DESC, created_at, id
                """
            )
        ).mappings().all()
    return {
        "candidates": [
            {
                "id": row["id"],
                "findingId": row["finding_id"],
                "target": row["target"],
                "actionCode": row["action_code"],
                "score": float(row["score"]),
                "status": row["status"],
                "createdAt": row["created_at"].isoformat(),
            }
            for row in rows
        ]
    }


@app.post("/api/v1/automation/candidates/{candidate_id}/request", status_code=201)
def request_automation_approval(
    candidate_id: str, payload: AutomationRequestInput, request: Request
) -> dict:
    _require_admin(request)
    with get_engine().begin() as connection:
        candidate = connection.execute(
            text(
                """
                SELECT c.id, c.target, c.action_code, c.status, f.id AS finding_id
                FROM automation_candidate c
                JOIN finding f ON f.id = c.finding_id
                WHERE c.id = :id
                """
            ),
            {"id": candidate_id},
        ).mappings().first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="candidate not found")
        decision = evaluate_automation(
            payload.manifest, candidate["action_code"], candidate["target"]
        )
        if not decision.allowed and not decision.approval_required:
            raise HTTPException(status_code=403, detail=decision.reason)
        if decision.allowed:
            connection.execute(
                text(
                    "UPDATE automation_candidate SET status = 'APPROVED', updated_at = :now WHERE id = :id"
                ),
                {"id": candidate_id, "now": datetime.now(timezone.utc)},
            )
            _audit(
                connection,
                request.state.user["sub"],
                "automation.auto_allowed",
                "AUTOMATION_CANDIDATE",
                candidate_id,
                candidate["target"],
                metadata={"reason": decision.reason, "tier": decision.tier},
            )
            return {"candidateId": candidate_id, "autoAllowed": True, "tier": decision.tier}
        request_id = f"automation-request-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        connection.execute(
            text(
                """
                INSERT INTO automation_request
                    (id, candidate_id, manifest, status, requested_by, created_at)
                VALUES (:id, :candidate_id, CAST(:manifest AS jsonb), 'PENDING', :requested_by, :now)
                """
            ),
            {
                "id": request_id,
                "candidate_id": candidate_id,
                "manifest": json.dumps(payload.manifest),
                "requested_by": request.state.user["sub"],
                "now": now,
            },
        )
        connection.execute(
            text(
                "UPDATE automation_candidate SET status = 'APPROVAL_REQUIRED', updated_at = :now WHERE id = :id"
            ),
            {"id": candidate_id, "now": now},
        )
        _audit(
            connection,
            request.state.user["sub"],
            "automation.approval_requested",
            "AUTOMATION_REQUEST",
            request_id,
            candidate["target"],
            metadata={"candidateId": candidate_id, "reason": decision.reason},
        )
    return {"candidateId": candidate_id, "requestId": request_id, "status": "PENDING"}


@app.get("/api/v1/automation/requests")
def automation_requests(request: Request) -> dict:
    _require_admin(request)
    with get_engine().connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT r.id, r.candidate_id, r.status, c.action_code, c.target,
                       r.requested_by, r.approved_by, r.reason, r.created_at, r.decided_at
                FROM automation_request r
                JOIN automation_candidate c ON c.id = r.candidate_id
                ORDER BY r.created_at DESC, r.id
                """
            )
        ).mappings().all()
    return {
        "requests": [
            {
                "id": row["id"],
                "candidateId": row["candidate_id"],
                "actionCode": row["action_code"],
                "target": row["target"],
                "status": row["status"],
                "requestedBy": row["requested_by"],
                "approvedBy": row["approved_by"],
                "reason": row["reason"],
                "createdAt": row["created_at"].isoformat(),
                "decidedAt": row["decided_at"].isoformat() if row["decided_at"] else None,
            }
            for row in rows
        ]
    }


@app.post("/api/v1/automation/requests/{request_id}/approve")
def approve_automation_request(
    request_id: str, payload: AutomationDecisionInput, request: Request
) -> dict:
    _require_admin(request)
    with get_engine().begin() as connection:
        pending = connection.execute(
            text(
                """
                SELECT r.id, r.candidate_id, r.status
                FROM automation_request r WHERE r.id = :id FOR UPDATE
                """
            ),
            {"id": request_id},
        ).mappings().first()
        if pending is None:
            raise HTTPException(status_code=404, detail="automation request not found")
        if pending["status"] != "PENDING":
            raise HTTPException(status_code=409, detail="automation request is not pending")
        now = datetime.now(timezone.utc)
        connection.execute(
            text(
                """
                UPDATE automation_request
                SET status = 'APPROVED', approved_by = :user, reason = :reason, decided_at = :now
                WHERE id = :id
                """
            ),
            {
                "id": request_id,
                "user": request.state.user["sub"],
                "reason": payload.reason,
                "now": now,
            },
        )
        connection.execute(
            text(
                "UPDATE automation_candidate SET status = 'APPROVED', updated_at = :now WHERE id = :id"
            ),
            {"id": pending["candidate_id"], "now": now},
        )
        _audit(
            connection,
            request.state.user["sub"],
            "automation.approved",
            "AUTOMATION_REQUEST",
            request_id,
            pending["candidate_id"],
            metadata={"reason": payload.reason},
        )
    return {"requestId": request_id, "status": "APPROVED"}


@app.post("/api/v1/automation/requests/{request_id}/reject")
def reject_automation_request(
    request_id: str, payload: AutomationDecisionInput, request: Request
) -> dict:
    _require_admin(request)
    with get_engine().begin() as connection:
        pending = connection.execute(
            text(
                "SELECT id, candidate_id, status FROM automation_request WHERE id = :id FOR UPDATE"
            ),
            {"id": request_id},
        ).mappings().first()
        if pending is None:
            raise HTTPException(status_code=404, detail="automation request not found")
        if pending["status"] != "PENDING":
            raise HTTPException(status_code=409, detail="automation request is not pending")
        now = datetime.now(timezone.utc)
        connection.execute(
            text(
                """
                UPDATE automation_request
                SET status = 'REJECTED', approved_by = :user, reason = :reason, decided_at = :now
                WHERE id = :id
                """
            ),
            {
                "id": request_id,
                "user": request.state.user["sub"],
                "reason": payload.reason,
                "now": now,
            },
        )
        connection.execute(
            text(
                "UPDATE automation_candidate SET status = 'REJECTED', updated_at = :now WHERE id = :id"
            ),
            {"id": pending["candidate_id"], "now": now},
        )
        _audit(
            connection,
            request.state.user["sub"],
            "automation.rejected",
            "AUTOMATION_REQUEST",
            request_id,
            pending["candidate_id"],
            outcome="DENIED",
            metadata={"reason": payload.reason},
        )
    return {"requestId": request_id, "status": "REJECTED"}


@app.post("/api/v1/automation/candidates/{candidate_id}/execute")
def execute_automation_candidate(
    candidate_id: str, payload: AutomationExecuteInput, request: Request
) -> dict:
    _require_admin(request)
    with get_engine().begin() as connection:
        candidate = connection.execute(
            text(
                """
                SELECT c.id, c.target, c.action_code, c.status,
                       c.finding_id, f.project_id
                FROM automation_candidate c
                JOIN finding f ON f.id = c.finding_id
                WHERE c.id = :id FOR UPDATE
                """
            ),
            {"id": candidate_id},
        ).mappings().first()
        if candidate is None:
            raise HTTPException(status_code=404, detail="candidate not found")
        if candidate["status"] not in {"QUEUED", "APPROVED"}:
            raise HTTPException(status_code=409, detail="candidate is not executable")
        decision = evaluate_automation(
            payload.manifest, candidate["action_code"], candidate["target"]
        )
        if decision.tier is not None and decision.tier >= 2:
            raise HTTPException(
                status_code=409,
                detail="state-changing execution is not implemented in L3-C",
            )
        if not decision.allowed or decision.approval_required:
            raise HTTPException(status_code=403, detail=decision.reason)
        allowed_hosts = {
            urlparse(value if "://" in value else f"http://{value}/").hostname
            for value in (payload.manifest.get("targets") or [])
            if urlparse(value if "://" in value else f"http://{value}/").hostname
        }
        sandbox = SandboxHttp()
        before = sandbox.capture(candidate["target"], allowed_hosts)
        if decision.tier == 0:
            result = ReadOnlyExecutor().execute(
                decision, candidate["target"], allowed_hosts
            )
        else:
            result = SafePocExecutor().execute(
                decision, candidate["target"], allowed_hosts
            )
        after = sandbox.capture(candidate["target"], allowed_hosts)
        state_mismatch = before.status != after.status
        execution_id = f"automation-exec-{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        connection.execute(
            text(
                """
                INSERT INTO automation_execution
                    (id, candidate_id, action_code, target, status,
                     before_hash, after_hash, http_status, observations, created_by, created_at)
                VALUES (:id, :candidate_id, :action_code, :target, :status,
                        :before_hash, :after_hash, :http_status, CAST(:observations AS jsonb),
                        :created_by, :now)
                """
            ),
            {
                "id": execution_id,
                "candidate_id": candidate_id,
                "action_code": decision.action,
                "target": candidate["target"],
                "status": "SNAPSHOT_MISMATCH" if state_mismatch else "SUCCEEDED",
                "before_hash": before.body_sha256,
                "after_hash": after.body_sha256,
                "http_status": result.status,
                "observations": json.dumps(
                    {
                        "result": result.observations,
                        "beforeStatus": before.status,
                        "afterStatus": after.status,
                        "bytesRead": result.bytes_read,
                    }
                ),
                "created_by": request.state.user["sub"],
                "now": now,
            },
        )
        connection.execute(
            text(
                "UPDATE automation_candidate SET status = 'EXECUTED', updated_at = :now WHERE id = :id"
            ),
            {"id": candidate_id, "now": now},
        )
        _audit(
            connection,
            request.state.user["sub"],
            "automation.executed",
            "AUTOMATION_CANDIDATE",
            candidate_id,
            candidate["target"],
            metadata={
                "executionId": execution_id,
                "actionCode": decision.action,
                "beforeHash": before.body_sha256,
                "afterHash": after.body_sha256,
                "snapshotMismatch": state_mismatch,
            },
        )
    return {
        "executionId": execution_id,
        "candidateId": candidate_id,
        "actionCode": decision.action,
        "target": candidate["target"],
        "httpStatus": result.status,
        "beforeHash": before.body_sha256,
        "afterHash": after.body_sha256,
        "snapshotMismatch": state_mismatch,
        "observations": result.observations,
    }


@app.post("/api/v1/automation/check")
def automation_check(payload: AutomationCheckInput, request: Request) -> dict:
    _require_admin(request)
    decision = evaluate_automation(
        payload.manifest,
        payload.actionCode,
        payload.target,
        used_actions=payload.usedActions,
    )
    with get_engine().begin() as connection:
        _audit(
            connection,
            request.state.user["sub"],
            "automation.check",
            "AUTOMATION_ACTION",
            payload.actionCode,
            payload.target,
            outcome="SUCCESS" if decision.allowed else "DENIED",
            metadata={
                "engagementId": payload.manifest.get("engagementId"),
                "target": payload.target,
                "actionCode": payload.actionCode,
                "approvalRequired": decision.approval_required,
                "reason": decision.reason,
            },
        )
    return asdict(decision)


@app.get("/api/v1/scan-profiles")
def scan_profiles() -> list[dict[str, str]]:
    query = text(
        "SELECT id, name, adapter_code FROM scan_profile ORDER BY id"
    )
    with get_engine().connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [dict(row) for row in rows]


@app.get("/api/v1/projects")
def projects() -> list[dict]:
    query = text(
        """
        SELECT id, name, scope, status, created_on
        FROM project
        ORDER BY created_on DESC, id
        """
    )
    with get_engine().connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "scope": row["scope"],
            "status": row["status"],
            "createdOn": row["created_on"].isoformat(),
        }
        for row in rows
    ]


@app.get("/api/v1/findings")
def findings() -> list[dict]:
    query = text(
        """
        SELECT id, project_id, target_id, title, severity, status, created_at
        FROM finding
        ORDER BY created_at DESC, id
        """
    )
    with get_engine().connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [
        {
            "id": row["id"],
            "projectId": row["project_id"],
            "targetId": row["target_id"],
            "title": row["title"],
            "severity": row["severity"],
            "status": row["status"],
            "createdAt": row["created_at"].isoformat(),
        }
        for row in rows
    ]


@app.get("/api/v1/reports")
def reports() -> list[dict]:
    query = text(
        """
        SELECT id, project_id, title, status, created_at
        FROM report
        ORDER BY created_at DESC, id
        """
    )
    with get_engine().connect() as connection:
        rows = connection.execute(query).mappings().all()
    return [
        {
            "id": row["id"],
            "projectId": row["project_id"],
            "title": row["title"],
            "status": row["status"],
            "createdAt": row["created_at"].isoformat(),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Read-only corpus pilot views. These are isolated from the public seed tables
# and are explicitly labelled as pilot, uncalibrated data.
# ---------------------------------------------------------------------------


def _corpus_limit(request: Request, default: int) -> int:
    raw = request.query_params.get("limit", str(default))
    try:
        value = int(raw)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="limit must be an integer") from error
    return max(1, min(value, 500))


@app.get("/api/v1/corpus/projects")
def corpus_projects(request: Request) -> dict:
    _require_admin(request)
    with get_engine().connect() as connection:
        project = connection.execute(
            text(
                """
                SELECT id, name, status, scope, created_at
                FROM corpus_pilot.project
                ORDER BY created_at, id
                """
            )
        ).mappings().first()
        if project is None:
            raise HTTPException(status_code=404, detail="corpus project not found")
        targets = connection.execute(
            text(
                """
                SELECT t.id, t.name, t.type, count(f.id) AS findings
                FROM corpus_pilot.target t
                LEFT JOIN corpus_pilot.finding f ON f.target_id = t.id
                WHERE t.project_id = :project_id
                GROUP BY t.id, t.name, t.type
                ORDER BY t.name
                """
            ),
            {"project_id": project["id"]},
        ).mappings().all()
    return {
        "pilot": True,
        "scoreLabel": "pilot-uncalibrated",
        "project": {
            "id": project["id"],
            "name": project["name"],
            "status": project["status"],
            "scope": project["scope"],
            "createdAt": project["created_at"].isoformat(),
        },
        "targets": [
            {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "findings": int(row["findings"]),
            }
            for row in targets
        ],
    }


@app.get("/api/v1/corpus/findings")
def corpus_findings(request: Request) -> dict:
    _require_admin(request)
    limit = _corpus_limit(request, 100)
    target = request.query_params.get("targetId", "")
    with get_engine().connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT f.id, f.source_id, f.target_id, f.title, f.severity, f.cwe,
                       f.location, f.verified, c.score, c.action_code
                FROM corpus_pilot.finding f
                LEFT JOIN corpus_pilot.candidate c ON c.finding_id = f.id
                WHERE (:target = '' OR f.target_id = :target)
                ORDER BY c.score DESC NULLS LAST, f.id
                LIMIT :limit
                """
            ),
            {"target": target, "limit": limit},
        ).mappings().all()
    return {
        "pilot": True,
        "scoreLabel": "pilot-uncalibrated",
        "findings": [
            {
                "id": row["id"],
                "sourceId": row["source_id"],
                "targetId": row["target_id"],
                "title": row["title"],
                "severity": row["severity"],
                "cwe": row["cwe"],
                "location": row["location"],
                "verified": bool(row["verified"]),
                "score": float(row["score"]) if row["score"] is not None else None,
                "actionCode": row["action_code"],
            }
            for row in rows
        ],
    }


@app.get("/api/v1/corpus/candidates")
def corpus_candidates(request: Request) -> dict:
    _require_admin(request)
    limit = _corpus_limit(request, 50)
    with get_engine().connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT c.id, c.finding_id, c.target, c.action_code, c.score, c.status,
                       c.model, f.source_id, f.title, f.verified
                FROM corpus_pilot.candidate c
                JOIN corpus_pilot.finding f ON f.id = c.finding_id
                ORDER BY c.score DESC, c.id
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    return {
        "pilot": True,
        "scoreLabel": "pilot-uncalibrated",
        "candidates": [
            {
                "id": row["id"],
                "findingId": row["finding_id"],
                "sourceId": row["source_id"],
                "title": row["title"],
                "target": row["target"],
                "actionCode": row["action_code"],
                "score": float(row["score"]),
                "status": row["status"],
                "model": row["model"],
                "verified": bool(row["verified"]),
            }
            for row in rows
        ],
    }
