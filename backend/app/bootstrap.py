from __future__ import annotations

from sqlalchemy import text

from .db import get_engine

SCAN_PROFILE = {
    "external_attack_surface": "External attack surface",
    "api_authorization": "API authorization",
    "cloud_configuration": "Cloud configuration",
}
SCAN_STATUS = {
    "QUEUED": "Queued",
    "RUNNING": "Running",
    "COMPLETED": "Completed",
    "FAILED": "Failed",
    "CANCELLED": "Cancelled",
}
SEVERITY = {
    "CRITICAL": "Critical",
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
}
FINDING_STATUS = {
    "NEW": "New",
    "CONFIRMED": "Confirmed",
    "IN_PROGRESS": "In Progress",
    "RESOLVED": "Resolved",
    "REOPENED": "Reopened",
    "ACCEPTED_RISK": "Accepted Risk",
    "FALSE_POSITIVE": "False Positive",
}
REPORT_STATUS = {"DRAFT": "Draft", "PUBLISHED": "Published"}
AUDIT_OUTCOME = {
    "SUCCESS": "Success",
    "SIMULATED": "Simulated",
    "DENIED": "Denied",
    "FAILURE": "Failure",
}
TARGET_TYPE = {"WEB": "Web", "API": "API", "CLOUD": "Cloud"}


def _rows(query: str) -> list[dict]:
    with get_engine().connect() as connection:
        return [dict(row) for row in connection.execute(text(query)).mappings().all()]


def build_bootstrap() -> dict:
    projects = _rows(
        """
        SELECT p.id, p.name, u.display_name AS owner, p.scope, p.status, p.created_on
        FROM project p LEFT JOIN app_user u ON u.id = p.owner_id
        ORDER BY p.created_on DESC, p.id
        """
    )
    targets = _rows(
        """
        SELECT t.id, t.project_id, t.name, t.type, t.scope,
               EXISTS (
                   SELECT 1 FROM target_authorization a
                   WHERE a.target_id = t.id AND a.revoked_at IS NULL
               ) AS authorized
        FROM target t ORDER BY t.id
        """
    )
    scans = _rows(
        """
        SELECT j.id, j.project_id, j.target_id, j.name, j.profile_id, j.status,
               j.created_at, r.progress, r.finished_at
        FROM scan_job j
        LEFT JOIN scan_run r ON r.job_id = j.id AND r.attempt = 1
        ORDER BY j.created_at DESC, j.id
        """
    )
    findings = _rows(
        """
        SELECT f.id, f.project_id, f.target_id, f.job_id, f.title, f.severity,
               f.status, f.notes, f.cwe, f.location, f.created_at, e.content AS evidence
        FROM finding f
        LEFT JOIN evidence e ON e.finding_id = f.id
        ORDER BY f.created_at DESC, f.id
        """
    )
    analyses = _rows(
        """
        SELECT a.id, a.finding_id, m.name AS model, mv.version, a.status,
               a.confidence, a.summary, a.limitations, a.created_at, a.simulated
        FROM analysis a
        JOIN model_version mv ON mv.id = a.model_version_id
        JOIN model m ON m.id = mv.model_id
        ORDER BY a.created_at DESC, a.id
        """
    )
    remediations = _rows(
        """
        SELECT r.id, r.finding_id, u.display_name AS assignee, r.due_date,
               r.status, r.notes
        FROM remediation r LEFT JOIN app_user u ON u.id = r.assignee_id
        ORDER BY r.created_at DESC, r.id
        """
    )
    reports = _rows(
        """
        SELECT id, project_id, job_id, title, status, created_at
        FROM report ORDER BY created_at DESC, id
        """
    )
    audit = _rows(
        """
        SELECT id, occurred_at, actor_label, action, resource_name, outcome
        FROM audit_event ORDER BY occurred_at DESC, id
        """
    )
    models = _rows(
        """
        SELECT m.id, m.name, mv.version, mv.stage, mv.metrics
        FROM model_version mv JOIN model m ON m.id = mv.model_id
        ORDER BY m.id, mv.created_at DESC
        """
    )
    datasets = _rows(
        """
        SELECT d.id, d.name, dv.version, dv.sample_count, d.provenance,
               dv.label_distribution
        FROM dataset_version dv JOIN dataset d ON d.id = dv.dataset_id
        ORDER BY d.id, dv.created_at DESC
        """
    )

    def pct(labels: dict) -> str:
        return " · ".join(
            f"{key.title()} {round(value * 100)}%" for key, value in labels.items()
        )

    return {
        "projects": [
            {
                "id": row["id"],
                "name": row["name"],
                "owner": row["owner"],
                "status": "Active" if row["status"] == "ACTIVE" else "Archived",
                "scope": row["scope"],
                "createdAt": row["created_on"].isoformat(),
            }
            for row in projects
        ],
        "targets": [
            {
                "id": row["id"],
                "projectId": row["project_id"],
                "name": row["name"],
                "type": TARGET_TYPE.get(row["type"], row["type"]),
                "authorized": bool(row["authorized"]),
                "scope": row["scope"],
                "status": "Monitored" if row["authorized"] else "Blocked",
            }
            for row in targets
        ],
        "scans": [
            {
                "id": row["id"],
                "projectId": row["project_id"],
                "targetId": row["target_id"],
                "name": row["name"],
                "profile": SCAN_PROFILE.get(row["profile_id"], row["profile_id"]),
                "status": SCAN_STATUS.get(row["status"], row["status"]),
                "progress": row["progress"] or 0,
                "simulated": True,
                "createdAt": row["created_at"].isoformat(),
                "completedAt": row["finished_at"].isoformat() if row["finished_at"] else None,
            }
            for row in scans
        ],
        "findings": [
            {
                "id": row["id"],
                "scanId": row["job_id"],
                "projectId": row["project_id"],
                "targetId": row["target_id"],
                "title": row["title"],
                "severity": SEVERITY.get(row["severity"], row["severity"]),
                "status": FINDING_STATUS.get(row["status"], row["status"]),
                "evidence": row["evidence"] or "",
                "createdAt": row["created_at"].isoformat(),
                "notes": row["notes"] or "",
                "cwe": row["cwe"],
                "location": row["location"] or {},
            }
            for row in findings
        ],
        "analyses": [
            {
                "id": row["id"],
                "findingId": row["finding_id"],
                "model": row["model"],
                "version": row["version"],
                "status": "Completed",
                "confidence": round(float(row["confidence"]) * 100),
                "summary": row["summary"],
                "limitations": row["limitations"],
                "createdAt": row["created_at"].isoformat(),
                "simulated": bool(row["simulated"]),
            }
            for row in analyses
        ],
        "remediations": [
            {
                "id": row["id"],
                "findingId": row["finding_id"],
                "assignee": row["assignee"],
                "dueDate": row["due_date"].isoformat() if row["due_date"] else "",
                "status": {
                    "IN_PROGRESS": "In Progress",
                    "COMPLETED": "Completed",
                    "REOPENED": "Reopened",
                    "CANCELLED": "Cancelled",
                }.get(row["status"], row["status"]),
                "notes": row["notes"] or "",
                "verification": None,
            }
            for row in remediations
        ],
        "reports": [
            {
                "id": row["id"],
                "projectId": row["project_id"],
                "scanId": row["job_id"],
                "title": row["title"],
                "status": REPORT_STATUS.get(row["status"], row["status"]),
                "createdAt": row["created_at"].isoformat(),
            }
            for row in reports
        ],
        "audit": [
            {
                "id": row["id"],
                "at": row["occurred_at"].isoformat(),
                "actor": row["actor_label"],
                "action": row["action"],
                "resource": row["resource_name"],
                "outcome": AUDIT_OUTCOME.get(row["outcome"], row["outcome"]),
            }
            for row in audit
        ],
        "models": [
            {
                "id": row["id"],
                "name": row["name"],
                "version": row["version"],
                "status": "Production" if row["stage"] == "PRODUCTION" else row["stage"].title(),
                "precision": f"Sample {row['metrics'].get('precision')}",
                "recall": f"Sample {row['metrics'].get('recall')}",
                "f1": f"Sample {row['metrics'].get('f1')}",
                "inference": f"Sample {row['metrics'].get('inferenceMs')} ms",
            }
            for row in models
        ],
        "datasets": [
            {
                "id": row["id"],
                "name": row["name"],
                "version": row["version"],
                "samples": row["sample_count"],
                "provenance": row["provenance"],
                "labels": pct(row["label_distribution"]),
            }
            for row in datasets
        ],
    }
