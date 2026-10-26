from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

import psycopg

DSN = os.getenv(
    "SEED_DSN",
    "postgresql://sentrix_migrator@10.20.10.20:5432/sentrix",
)

FIXED_CREATED = "2026-09-15T00:00:00Z"
PROMPT_CONTENT = (
    "Assess the supplied finding for business impact. Return a concise, "
    "evidence-grounded risk summary. Mark simulated output as simulated."
)
PROMPT_HASH = hashlib.sha256(PROMPT_CONTENT.encode()).hexdigest()
DATASET_HASH = hashlib.sha256(b"sample/demo dataset 2026.09").hexdigest()
DEMO_PASSWORD_HASH = (
    "pbkdf2_sha256$210000$c2VudHJpeC1kZW1vLXNhbHQtMjAyNg==$"
    "k6NqX1c1yFEYjhysoIi74amtyCuw8Sp1jCeckFM/sko="
)
ADMIN_PASSWORD_HASH = (
    "pbkdf2_sha256$210000$c2VudHJpeC1hZG1pbi1zYWx0LTIwMjY=$"
    "hm2DNTRC0ttsgaFsbXjkpgvtgH//kcQjaiEfu7EYmOA="
)
EVIDENCE = {
    "evidence-bola": "Illustrative evidence: simulated response showed a tenant mismatch during an authorized demo replay.",
    "evidence-bucket": "Illustrative configuration observation from simulated scan output.",
    "evidence-debug": "Illustrative endpoint observation from simulated scan output.",
}


def rows() -> list[tuple[str, str, list[tuple], str]]:
    """Return (table, columns, values, conflict) entries in dependency order."""
    return [
        (
            "app_user",
            "id, display_name, email, role, password_hash, is_active, created_at",
            [
                ("user-maya", "Maya Chen", "maya@sentrix.local", "ANALYST", DEMO_PASSWORD_HASH, True, "2026-09-01T00:00:00Z"),
                ("user-jon", "Jon Bell", "jon@sentrix.local", "ANALYST", None, True, "2026-09-01T00:00:00Z"),
                ("user-priya", "Priya Nair", "priya@sentrix.local", "ANALYST", None, True, "2026-09-01T00:00:00Z"),
                ("user-admin", "Admin", "admin@sentrix.local", "ADMIN", ADMIN_PASSWORD_HASH, True, "2026-09-01T00:00:00Z"),
                ("user-system", "SENTRIX demo service", "system@sentrix.local", "ANALYST", None, False, "2026-09-01T00:00:00Z"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "project",
            "id, name, owner_id, scope, status, created_on, created_at, updated_at",
            [
                ("project-atlas", "Atlas Commerce", "user-maya", "Public web application and authenticated API", "ACTIVE", "2026-10-12", "2026-10-12T09:00:00Z", "2026-10-12T09:00:00Z"),
                ("project-helix", "Helix Payments", "user-jon", "Payment API and cloud configuration", "ACTIVE", "2026-10-09", "2026-10-09T09:00:00Z", "2026-10-09T09:00:00Z"),
                ("project-northstar", "Northstar API", "user-priya", "Public API endpoints", "ACTIVE", "2026-10-02", "2026-10-02T09:00:00Z", "2026-10-02T09:00:00Z"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "project_member",
            "project_id, user_id, role, created_at",
            [
                ("project-atlas", "user-maya", "OWNER", "2026-10-12T09:00:00Z"),
                ("project-helix", "user-jon", "OWNER", "2026-10-09T09:00:00Z"),
                ("project-northstar", "user-priya", "OWNER", "2026-10-02T09:00:00Z"),
            ],
            "(project_id, user_id) DO NOTHING",
        ),
        (
            "target",
            "id, project_id, name, type, scope, created_at, updated_at, created_by",
            [
                ("target-atlas-api", "project-atlas", "api.atlas.example", "API", "https://api.atlas.example/v2/*", "2026-10-12T09:05:00Z", "2026-10-12T09:05:00Z", "user-maya"),
                ("target-atlas-web", "project-atlas", "app.atlas.example", "WEB", "https://app.atlas.example/*", "2026-10-12T09:06:00Z", "2026-10-12T09:06:00Z", "user-maya"),
                ("target-helix-api", "project-helix", "payments.helix.example", "API", "https://payments.helix.example/*", "2026-10-09T09:05:00Z", "2026-10-09T09:05:00Z", "user-jon"),
                ("target-northstar", "project-northstar", "api.northstar.example", "API", "", "2026-10-02T09:05:00Z", "2026-10-02T09:05:00Z", "user-priya"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "target_authorization",
            "id, target_id, attested_by, attested_at, statement, scope_snapshot",
            [
                ("auth-atlas-api", "target-atlas-api", "user-maya", "2026-10-12T09:10:00Z", "I confirm I am authorized to test this target.", "https://api.atlas.example/v2/*"),
                ("auth-atlas-web", "target-atlas-web", "user-maya", "2026-10-12T09:11:00Z", "I confirm I am authorized to test this target.", "https://app.atlas.example/*"),
                ("auth-helix-api", "target-helix-api", "user-jon", "2026-10-09T09:10:00Z", "I confirm I am authorized to test this target.", "https://payments.helix.example/*"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "scan_job",
            "id, project_id, target_id, name, profile_id, status, created_at, updated_at, created_by",
            [
                ("scan-atlas", "project-atlas", "target-atlas-api", "External perimeter review", "external_attack_surface", "COMPLETED", "2026-10-18T02:20:00.000Z", "2026-10-18T02:43:00.000Z", "user-maya"),
                ("scan-helix", "project-helix", "target-helix-api", "API authorization audit", "api_authorization", "COMPLETED", "2026-10-18T00:12:00.000Z", "2026-10-18T00:35:00.000Z", "user-jon"),
                ("scan-atlas-running", "project-atlas", "target-atlas-web", "Web configuration review", "external_attack_surface", "RUNNING", "2026-10-18T03:44:00.000Z", "2026-10-18T03:44:00.000Z", "user-maya"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "scan_run",
            "id, job_id, attempt, status, progress, adapter_code, worker_id, started_at, finished_at, heartbeat_at, stats, created_at",
            [
                ("run-seed-atlas", "scan-atlas", 1, "SUCCEEDED", 100, "demo", "seed", "2026-10-18T02:20:00.000Z", "2026-10-18T02:43:00.000Z", "2026-10-18T02:43:00.000Z", json.dumps({"seed": True}), "2026-10-18T02:20:00.000Z"),
                ("run-seed-helix", "scan-helix", 1, "SUCCEEDED", 100, "demo", "seed", "2026-10-18T00:12:00.000Z", "2026-10-18T00:35:00.000Z", "2026-10-18T00:35:00.000Z", json.dumps({"seed": True}), "2026-10-18T00:12:00.000Z"),
                ("run-seed-atlas-running", "scan-atlas-running", 1, "RUNNING", 78, "demo", "seed", "2026-10-18T03:44:00.000Z", None, "2026-10-18T03:44:00.000Z", json.dumps({"seed": True}), "2026-10-18T03:44:00.000Z"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "finding",
            "id, project_id, target_id, job_id, run_id, observation_id, dedup_key, title, severity, status, notes, source, created_at, created_by, updated_at",
            [
                ("finding-bola", "project-atlas", "target-atlas-api", "scan-atlas", "run-seed-atlas", None, "finding-bola", "Broken object-level authorization", "CRITICAL", "CONFIRMED", "Validate ownership checks before remediation.", "DEMO", "2026-10-18T02:43:00.000Z", "user-maya", "2026-10-18T02:43:00.000Z"),
                ("finding-bucket", "project-helix", "target-helix-api", "scan-helix", "run-seed-helix", None, "finding-bucket", "Public storage policy", "HIGH", "NEW", "", "DEMO", "2026-10-18T00:35:00.000Z", "user-jon", "2026-10-18T00:35:00.000Z"),
                ("finding-debug", "project-atlas", "target-atlas-web", "scan-atlas", "run-seed-atlas", None, "finding-debug", "Exposed debug endpoint", "MEDIUM", "ACCEPTED_RISK", "Risk owner accepted until next release.", "DEMO", "2026-10-17T18:06:00.000Z", "user-maya", "2026-10-17T18:06:00.000Z"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "evidence",
            "id, finding_id, run_id, kind, title, content, sha256, mime_type, captured_at, created_at, created_by",
            [
                ("evidence-bola", "finding-bola", "run-seed-atlas", "TEXT", "Simulated authorization observation", EVIDENCE["evidence-bola"], hashlib.sha256(EVIDENCE["evidence-bola"].encode()).hexdigest(), "text/plain", "2026-10-18T02:42:00.000Z", "2026-10-18T02:43:00.000Z", "user-maya"),
                ("evidence-bucket", "finding-bucket", "run-seed-helix", "TEXT", "Simulated storage observation", EVIDENCE["evidence-bucket"], hashlib.sha256(EVIDENCE["evidence-bucket"].encode()).hexdigest(), "text/plain", "2026-10-18T00:34:00.000Z", "2026-10-18T00:35:00.000Z", "user-jon"),
                ("evidence-debug", "finding-debug", "run-seed-atlas", "TEXT", "Simulated endpoint observation", EVIDENCE["evidence-debug"], hashlib.sha256(EVIDENCE["evidence-debug"].encode()).hexdigest(), "text/plain", "2026-10-17T18:05:00.000Z", "2026-10-17T18:06:00.000Z", "user-maya"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "finding_status_event",
            "id, finding_id, from_status, to_status, actor_id, reason, occurred_at",
            [
                ("fse-bola-created", "finding-bola", None, "CONFIRMED", "user-maya", "Imported from prototype seed.", "2026-10-18T02:43:00.000Z"),
                ("fse-bucket-created", "finding-bucket", None, "NEW", "user-jon", "Imported from prototype seed.", "2026-10-18T00:35:00.000Z"),
                ("fse-debug-created", "finding-debug", None, "ACCEPTED_RISK", "user-maya", "Imported from prototype seed.", "2026-10-17T18:06:00.000Z"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "prompt_template",
            "id, name, purpose, is_active, created_at",
            [("pt-risk", "Risk summary", "Summarize finding risk and business impact.", True, "2026-09-20T00:00:00Z")],
            "(id) DO NOTHING",
        ),
        (
            "prompt_template_version",
            "id, template_id, version, content, content_hash, created_at, created_by",
            [("ptv-risk-1", "pt-risk", "1", PROMPT_CONTENT, PROMPT_HASH, "2026-09-20T00:00:00Z", "user-admin")],
            "(id) DO NOTHING",
        ),
        (
            "model",
            "id, name, provider_type, description, created_at",
            [
                ("model-risk", "SENTRIX Risk Engine", "MOCK", "Demo risk summary model.", FIXED_CREATED),
                ("model-evidence", "Evidence Summarizer", "MOCK", "Demo evidence summarizer.", FIXED_CREATED),
            ],
            "(id) DO NOTHING",
        ),
        (
            "model_version",
            "id, model_id, version, stage, artifact_uri, artifact_sha256, metrics, is_mock, created_at, promoted_at",
            [
                ("modelversion-risk-4.8.2", "model-risk", "4.8.2", "PRODUCTION", "mock://risk-4.8.2", None, json.dumps({"precision": 0.91, "recall": 0.88, "f1": 0.89, "inferenceMs": 420}), True, "2026-09-15T00:00:00Z", "2026-09-15T00:00:00Z"),
                ("modelversion-evidence-2.4.1", "model-evidence", "2.4.1", "PRODUCTION", "mock://evidence-2.4.1", None, json.dumps({"precision": 0.86, "recall": 0.84, "f1": 0.85, "inferenceMs": 280}), True, "2026-09-15T00:00:00Z", "2026-09-15T00:00:00Z"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "dataset",
            "id, name, description, provenance, license, created_at",
            [("dataset-demo", "Demo vulnerability evaluation set", "Sample-only dataset", "Sample data - demo only", "sample/demo", FIXED_CREATED)],
            "(id) DO NOTHING",
        ),
        (
            "dataset_version",
            "id, dataset_id, version, sample_count, label_distribution, content_hash, created_at, created_by",
            [("datasetversion-demo-2026.09", "dataset-demo", "2026.09", 1280, json.dumps({"CRITICAL": 0.12, "HIGH": 0.28, "MEDIUM": 0.40, "LOW": 0.20}), DATASET_HASH, FIXED_CREATED, "user-admin")],
            "(id) DO NOTHING",
        ),
        (
            "analysis",
            "id, finding_id, model_version_id, prompt_template_version_id, status, confidence, summary, limitations, input_hash, latency_ms, simulated, created_at, completed_at",
            [
                ("analysis-bola", "finding-bola", "modelversion-risk-4.8.2", "ptv-risk-1", "COMPLETED", 0.91, "High-confidence authorization defect. Business impact is elevated because the affected asset processes customer orders.", "Mock inference for prototype demonstration only; not a scanner or trained-model result.", hashlib.sha256(b"analysis-bola").hexdigest(), 420, True, "2026-10-18T02:45:00.000Z", "2026-10-18T02:45:00.000Z"),
            ],
            "(id) DO NOTHING",
        ),
        (
            "remediation",
            "id, finding_id, assignee_id, due_date, status, notes, created_at, updated_at, created_by",
            [("task-bola", "finding-bola", "user-maya", "2026-10-24", "IN_PROGRESS", "Implement object ownership authorization on order reads.", "2026-10-18T02:50:00.000Z", "2026-10-18T02:50:00.000Z", "user-maya")],
            "(id) DO NOTHING",
        ),
        (
            "report",
            "id, project_id, job_id, title, status, snapshot_hash, created_at, created_by, published_at",
            [("report-atlas", "project-atlas", "scan-atlas", "Atlas Commerce - Security assessment", "PUBLISHED", hashlib.sha256(b"report-atlas").hexdigest(), "2026-10-18T03:00:00.000Z", "user-maya", "2026-10-18T03:00:00.000Z")],
            "(id) DO NOTHING",
        ),
        (
            "report_finding",
            "report_id, finding_id, position, severity, status, title, target_name, evidence_excerpt",
            [
                ("report-atlas", "finding-bola", 1, "CRITICAL", "CONFIRMED", "Broken object-level authorization", "api.atlas.example", EVIDENCE["evidence-bola"]),
                ("report-atlas", "finding-debug", 2, "MEDIUM", "ACCEPTED_RISK", "Exposed debug endpoint", "app.atlas.example", EVIDENCE["evidence-debug"]),
            ],
            "(report_id, finding_id) DO NOTHING",
        ),
        (
            "audit_event",
            "id, occurred_at, actor_id, actor_label, action, resource_type, resource_id, resource_name, outcome, request_id, metadata",
            [
                ("audit-seed-1", "2026-10-18T03:00:00.000Z", "user-maya", "Maya Chen", "Published report", "REPORT", "report-atlas", "Atlas Commerce security assessment", "SUCCESS", "seed", json.dumps({"seed": True})),
                ("audit-seed-2", "2026-10-18T02:45:00.000Z", "user-system", "SENTRIX demo service", "Completed AI analysis", "FINDING", "finding-bola", "Broken object-level authorization", "SIMULATED", "seed", json.dumps({"seed": True})),
            ],
            "(id) DO NOTHING",
        ),
    ]


def main() -> None:
    with psycopg.connect(DSN) as connection:
        with connection.cursor() as cursor:
            for table, columns, values, conflict in rows():
                placeholders = ", ".join(["%s"] * len(values[0]))
                sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) ON CONFLICT {conflict}"
                cursor.executemany(sql, values)
            cursor.execute("SELECT count(*) FROM app_user")
            users = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM finding")
            findings = cursor.fetchone()[0]
        connection.commit()
        print(f"seed complete: app_user={users}, finding={findings}")


if __name__ == "__main__":
    main()
