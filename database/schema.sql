-- =============================================================================
-- SENTRIX — Phase 2 schema (design artifact, NOT applied)
-- Target: PostgreSQL 16+ (illustrative; pin the engine version at implementation)
--
-- This file is part of the Phase 2 plan. It is not wired into the running
-- prototype, adds no dependency, and changes no existing file or ACL.
-- The repository's static server (server.mjs/static.js) continues to be the
-- only thing serving files; this schema is the proposed system of record for
-- the backend described in 02-architecture-and-security.md.
--
-- Conventions
--   * ids are opaque text: demo seed rows keep today's readable ids
--     (project-atlas, …) while generated rows use a prefixed ULID.
--   * enums are canonical UPPER_SNAKE codes; the frontend adapter maps them to
--     today's display strings ("In Progress", "Accepted Risk", …) — see 06 §5.
--   * timestamps are timestamptz (UTC). Date-only fields exist only where the
--     current UI already uses a date (project.created_on, remediation.due_date).
--   * append-only tables reject UPDATE/DELETE at trigger level and should also
--     have UPDATE/DELETE revoked from the application role (§ least privilege).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enumerated vocabularies
-- ---------------------------------------------------------------------------
CREATE TYPE user_role            AS ENUM ('ADMIN', 'ANALYST', 'VIEWER');
CREATE TYPE project_role         AS ENUM ('OWNER', 'ANALYST', 'VIEWER');
CREATE TYPE project_status       AS ENUM ('ACTIVE', 'ARCHIVED');
CREATE TYPE target_type          AS ENUM ('WEB', 'API', 'CLOUD');
CREATE TYPE scan_job_status      AS ENUM ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');
CREATE TYPE scan_run_status      AS ENUM ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'TIMED_OUT', 'CANCELLED');
CREATE TYPE finding_severity     AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');
CREATE TYPE finding_status       AS ENUM ('NEW', 'CONFIRMED', 'IN_PROGRESS', 'RESOLVED', 'REOPENED', 'ACCEPTED_RISK', 'FALSE_POSITIVE');
CREATE TYPE analysis_status      AS ENUM ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED');
CREATE TYPE remediation_status   AS ENUM ('IN_PROGRESS', 'COMPLETED', 'REOPENED', 'CANCELLED');
CREATE TYPE verification_outcome AS ENUM ('VERIFIED', 'REJECTED');
CREATE TYPE verification_method  AS ENUM ('RESCAN', 'AUTOMATED_TEST', 'MANUAL_REVIEW');
CREATE TYPE report_status        AS ENUM ('DRAFT', 'PUBLISHED');
CREATE TYPE evidence_kind        AS ENUM ('TEXT', 'HTTP_EXCHANGE', 'FILE', 'SCREENSHOT', 'CONFIG_SNIPPET', 'LOG_EXCERPT');
CREATE TYPE model_stage          AS ENUM ('CANDIDATE', 'STAGED', 'PRODUCTION', 'ARCHIVED');
CREATE TYPE evaluation_status    AS ENUM ('RUNNING', 'COMPLETED', 'FAILED');
CREATE TYPE evaluation_data_origin AS ENUM ('SIMULATED', 'MEASURED');
CREATE TYPE audit_outcome        AS ENUM ('SUCCESS', 'SIMULATED', 'DENIED', 'FAILURE');

-- ---------------------------------------------------------------------------
-- Identity and tenancy
-- ---------------------------------------------------------------------------
CREATE TABLE app_user (
    id            text PRIMARY KEY,
    display_name  text NOT NULL CHECK (btrim(display_name) <> ''),
    email         text NOT NULL,
    role          user_role NOT NULL DEFAULT 'ANALYST',
    password_hash text,                          -- NULL when an external IdP is used
    is_active     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX app_user_email_lower_uq ON app_user (lower(email));

CREATE TABLE project (
    id          text PRIMARY KEY,
    name        text NOT NULL CHECK (btrim(name) <> ''),
    owner_id    text NOT NULL REFERENCES app_user (id),
    scope       text NOT NULL DEFAULT 'Not configured',
    status      project_status NOT NULL DEFAULT 'ACTIVE',
    created_on  date NOT NULL DEFAULT (now() AT TIME ZONE 'utc')::date,  -- current UI format
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),   -- app-managed; optimistic checks
    archived_at timestamptz
);
CREATE UNIQUE INDEX project_name_lower_uq ON project (lower(name));  -- current rule: global, case-insensitive
CREATE INDEX project_status_idx ON project (status);

CREATE TABLE project_member (
    project_id text NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    user_id    text NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
    role       project_role NOT NULL DEFAULT 'ANALYST',
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, user_id)
);
CREATE INDEX project_member_user_idx ON project_member (user_id);

-- ---------------------------------------------------------------------------
-- Authorized targets and their attestation
-- ---------------------------------------------------------------------------
CREATE TABLE target (
    id         text PRIMARY KEY,
    project_id text NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    name       text NOT NULL CHECK (btrim(name) <> ''),
    type       target_type NOT NULL DEFAULT 'WEB',
    scope      text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by text NOT NULL REFERENCES app_user (id),
    UNIQUE (id, project_id)                       -- enables composite FKs below
);
CREATE INDEX target_project_idx ON target (project_id);

-- The checkbox in today's form becomes a stored attestation. A target is
-- "authorized" exactly when it has an active (non-revoked) attestation; the
-- API derives {authorized, status: MONITORED|BLOCKED} from this table.
CREATE TABLE target_authorization (
    id             text PRIMARY KEY,
    target_id      text NOT NULL REFERENCES target (id) ON DELETE CASCADE,
    attested_by    text NOT NULL REFERENCES app_user (id),
    attested_at    timestamptz NOT NULL DEFAULT now(),
    statement      text NOT NULL,
    scope_snapshot text NOT NULL,
    revoked_at     timestamptz
);
CREATE UNIQUE INDEX target_authorization_active_uq
    ON target_authorization (target_id) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------------
-- Scan profiles, jobs and runs
-- ---------------------------------------------------------------------------
CREATE TABLE scan_profile (
    id           text PRIMARY KEY,                 -- e.g. external_attack_surface
    name         text NOT NULL,                    -- "External attack surface"
    adapter_code text NOT NULL,                    -- "demo", "nuclei", …
    config       jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_active    boolean NOT NULL DEFAULT true
);

CREATE TABLE scan_job (
    id             text PRIMARY KEY,
    project_id     text NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    target_id      text NOT NULL,
    name           text NOT NULL CHECK (btrim(name) <> ''),
    profile_id     text NOT NULL REFERENCES scan_profile (id),
    status         scan_job_status NOT NULL DEFAULT 'QUEUED',
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),   -- optimistic concurrency (If-Match)
    created_by     text NOT NULL REFERENCES app_user (id),
    cancelled_at   timestamptz,
    failure_reason text,
    UNIQUE (id, project_id),
    CONSTRAINT scan_job_target_same_project
        FOREIGN KEY (target_id, project_id) REFERENCES target (id, project_id)
);
CREATE INDEX scan_job_project_idx ON scan_job (project_id, created_at DESC);
CREATE INDEX scan_job_target_idx ON scan_job (target_id);
CREATE INDEX scan_job_status_idx ON scan_job (status);

CREATE TABLE scan_run (
    id            text PRIMARY KEY,
    job_id        text NOT NULL REFERENCES scan_job (id) ON DELETE CASCADE,
    attempt       integer NOT NULL CHECK (attempt > 0),
    status        scan_run_status NOT NULL DEFAULT 'PENDING',
    progress      smallint NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    adapter_code  text NOT NULL,
    worker_id     text,
    started_at    timestamptz,
    finished_at   timestamptz,
    heartbeat_at  timestamptz,
    exit_code     integer,
    error_message text,
    stats         jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (job_id, attempt)
);
CREATE UNIQUE INDEX scan_run_one_active_uq
    ON scan_run (job_id) WHERE status IN ('PENDING', 'RUNNING');
CREATE INDEX scan_run_queue_idx ON scan_run (status, created_at);

-- Adapter-normalized scanner output. One observation may or may not become a
-- finding (deduplication happens in the service layer).
CREATE TABLE scan_observation (
    id            text PRIMARY KEY,
    run_id        text NOT NULL REFERENCES scan_run (id) ON DELETE CASCADE,
    fingerprint   text NOT NULL,
    scanner_code  text NOT NULL,
    rule_id       text,
    title         text NOT NULL,
    severity_raw  text NOT NULL,
    confidence    numeric(4,3) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    location      jsonb NOT NULL DEFAULT '{}'::jsonb,
    payload       jsonb NOT NULL DEFAULT '{}'::jsonb,   -- bounded, redacted raw output
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, fingerprint)
);
CREATE INDEX scan_observation_run_idx ON scan_observation (run_id);

-- ---------------------------------------------------------------------------
-- Findings and evidence
-- ---------------------------------------------------------------------------
CREATE TABLE finding (
    id                    text PRIMARY KEY,
    project_id            text NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    target_id             text NOT NULL,
    job_id                text,
    run_id                text REFERENCES scan_run (id) ON DELETE SET NULL,
    observation_id        text UNIQUE REFERENCES scan_observation (id) ON DELETE SET NULL,
    dedup_key             text,                    -- project-scoped scanner fingerprint
    title                 text NOT NULL CHECK (btrim(title) <> ''),
    severity              finding_severity NOT NULL,
    status                finding_status NOT NULL DEFAULT 'NEW',
    notes                 text NOT NULL DEFAULT '',
    cwe                   text,
    location              jsonb NOT NULL DEFAULT '{}'::jsonb,
    source                text NOT NULL DEFAULT 'SCANNER' CHECK (source IN ('SCANNER', 'MANUAL', 'DEMO')),
    created_at            timestamptz NOT NULL DEFAULT now(),
    created_by            text REFERENCES app_user (id),
    updated_at            timestamptz NOT NULL DEFAULT now(),
    resolved_at           timestamptz,
    CONSTRAINT finding_target_same_project
        FOREIGN KEY (target_id, project_id) REFERENCES target (id, project_id),
    CONSTRAINT finding_job_same_project
        FOREIGN KEY (job_id, project_id) REFERENCES scan_job (id, project_id)
);
CREATE UNIQUE INDEX finding_dedup_uq
    ON finding (project_id, dedup_key) WHERE dedup_key IS NOT NULL;
CREATE INDEX finding_project_idx ON finding (project_id, created_at DESC);
CREATE INDEX finding_job_idx ON finding (job_id);
CREATE INDEX finding_status_idx ON finding (status);
CREATE INDEX finding_severity_idx ON finding (severity);

-- Every finding status change, including automated ones, with the reason.
-- RESOLVED rows must reference the verification that caused them; this is the
-- database-side anchor for the rule "a remediation is not a resolution".
CREATE TABLE finding_status_event (
    id              text PRIMARY KEY,
    finding_id      text NOT NULL REFERENCES finding (id) ON DELETE CASCADE,
    from_status     finding_status,
    to_status       finding_status NOT NULL,
    actor_id        text REFERENCES app_user (id),
    reason          text NOT NULL DEFAULT '',
    verification_id text,                          -- FK added after verification exists
    occurred_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX finding_status_event_finding_idx ON finding_status_event (finding_id, occurred_at);

CREATE TABLE evidence (
    id          text PRIMARY KEY,
    finding_id  text NOT NULL REFERENCES finding (id) ON DELETE CASCADE,
    run_id      text REFERENCES scan_run (id) ON DELETE SET NULL,
    kind        evidence_kind NOT NULL,
    title       text NOT NULL DEFAULT '',
    content     text,                              -- inline, redacted excerpt
    storage_uri text,                              -- content-addressed artifact key
    sha256      text CHECK (sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'),
    size_bytes  bigint CHECK (size_bytes IS NULL OR size_bytes >= 0),
    mime_type   text,
    captured_at timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  text REFERENCES app_user (id),
    CONSTRAINT evidence_has_content CHECK (content IS NOT NULL OR storage_uri IS NOT NULL)
);
CREATE INDEX evidence_finding_idx ON evidence (finding_id);

CREATE TABLE artifact (
    sha256      text PRIMARY KEY CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    project_id  text NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    evidence_id text REFERENCES evidence (id) ON DELETE SET NULL,
    created_by  text NOT NULL REFERENCES app_user (id),
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX artifact_project_idx ON artifact (project_id);

-- ---------------------------------------------------------------------------
-- AI analyses, models, datasets and evaluations
-- ---------------------------------------------------------------------------
CREATE TABLE model (
    id            text PRIMARY KEY,
    name          text NOT NULL,
    provider_type text NOT NULL DEFAULT 'MOCK',    -- MOCK | HTTP | …
    description   text NOT NULL DEFAULT '',
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE model_version (
    id                          text PRIMARY KEY,
    model_id                    text NOT NULL REFERENCES model (id) ON DELETE CASCADE,
    version                     text NOT NULL,
    stage                       model_stage NOT NULL DEFAULT 'CANDIDATE',
    artifact_uri                text,
    artifact_sha256             text CHECK (artifact_sha256 IS NULL OR artifact_sha256 ~ '^[0-9a-f]{64}$'),
    training_dataset_version_id text,              -- FK added after dataset_version exists
    metrics                     jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_mock                     boolean NOT NULL DEFAULT false,
    created_at                  timestamptz NOT NULL DEFAULT now(),
    promoted_at                 timestamptz,
    UNIQUE (model_id, version)
);
CREATE INDEX model_version_stage_idx ON model_version (stage);
CREATE UNIQUE INDEX model_version_one_production_uq
    ON model_version (model_id) WHERE stage = 'PRODUCTION';

-- Prompt templates are versioned and immutable. An analysis always pins the
-- exact prompt-template version it used, so the report can be reproduced.
CREATE TABLE prompt_template (
    id         text PRIMARY KEY,
    name       text NOT NULL CHECK (btrim(name) <> ''),
    purpose    text NOT NULL DEFAULT '',
    is_active  boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE prompt_template_version (
    id            text PRIMARY KEY,
    template_id   text NOT NULL REFERENCES prompt_template (id) ON DELETE CASCADE,
    version       text NOT NULL CHECK (btrim(version) <> ''),
    content       text NOT NULL CHECK (btrim(content) <> ''),  -- template body, no secrets
    content_hash  text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    created_at    timestamptz NOT NULL DEFAULT now(),
    created_by    text NOT NULL REFERENCES app_user (id),
    UNIQUE (template_id, version)
);
CREATE INDEX prompt_template_version_template_idx ON prompt_template_version (template_id);

CREATE TABLE analysis (
    id                        text PRIMARY KEY,
    finding_id                text NOT NULL REFERENCES finding (id) ON DELETE CASCADE,
    model_version_id          text NOT NULL REFERENCES model_version (id),
    prompt_template_version_id text NOT NULL REFERENCES prompt_template_version (id),
    status                    analysis_status NOT NULL DEFAULT 'QUEUED',
    confidence                numeric(5,4) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    summary                   text,
    limitations               text,
    input_hash                text,
    latency_ms                integer CHECK (latency_ms IS NULL OR latency_ms >= 0),
    simulated                 boolean NOT NULL DEFAULT false,
    failure_reason            text,
    created_at                timestamptz NOT NULL DEFAULT now(),
    completed_at              timestamptz
);
-- Today the UI assumes at most one analysis per finding; enforce one "live" row
-- while allowing retries after FAILED.
CREATE UNIQUE INDEX analysis_live_uq
    ON analysis (finding_id) WHERE status IN ('QUEUED', 'RUNNING', 'COMPLETED');
CREATE INDEX analysis_finding_idx ON analysis (finding_id);

CREATE TABLE dataset (
    id          text PRIMARY KEY,
    name        text NOT NULL,
    description text NOT NULL DEFAULT '',
    provenance  text NOT NULL DEFAULT '',
    license     text NOT NULL DEFAULT '',
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE dataset_version (
    id                text PRIMARY KEY,
    dataset_id        text NOT NULL REFERENCES dataset (id) ON DELETE CASCADE,
    version           text NOT NULL,
    sample_count      integer NOT NULL CHECK (sample_count >= 0),
    label_distribution jsonb NOT NULL DEFAULT '{}'::jsonb,
    content_hash      text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    created_at        timestamptz NOT NULL DEFAULT now(),
    created_by        text REFERENCES app_user (id),
    UNIQUE (dataset_id, version)
);

CREATE TABLE evaluation_run (
    id                text PRIMARY KEY,
    model_version_id  text NOT NULL REFERENCES model_version (id) ON DELETE CASCADE,
    dataset_version_id text NOT NULL REFERENCES dataset_version (id),
    status            evaluation_status NOT NULL DEFAULT 'RUNNING',
    data_origin       evaluation_data_origin NOT NULL DEFAULT 'SIMULATED',
    metrics           jsonb NOT NULL DEFAULT '{}'::jsonb,
    environment       jsonb NOT NULL DEFAULT '{}'::jsonb,  -- image digest, hardware
    seed              bigint,
    started_at        timestamptz NOT NULL DEFAULT now(),
    finished_at       timestamptz,
    created_by        text REFERENCES app_user (id),
    -- A MEASURED run must carry a seed and a non-empty metrics object; a
    -- SIMULATED run must never be presented as a measurement (API contract).
    CONSTRAINT evaluation_measured_requires_evidence CHECK (
        data_origin = 'SIMULATED'
        OR (seed IS NOT NULL AND finished_at IS NOT NULL AND metrics <> '{}'::jsonb)
    )
);
CREATE INDEX evaluation_run_model_idx ON evaluation_run (model_version_id);
CREATE INDEX evaluation_run_dataset_idx ON evaluation_run (dataset_version_id);

-- ---------------------------------------------------------------------------
-- Remediation and verification
-- ---------------------------------------------------------------------------
CREATE TABLE remediation (
    id          text PRIMARY KEY,
    finding_id  text NOT NULL REFERENCES finding (id) ON DELETE CASCADE,
    assignee_id text NOT NULL REFERENCES app_user (id),
    due_date    date,
    status      remediation_status NOT NULL DEFAULT 'IN_PROGRESS',
    notes       text NOT NULL DEFAULT '',
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    created_by  text NOT NULL REFERENCES app_user (id),
    closed_at   timestamptz,
    reopened_at timestamptz
);
CREATE INDEX remediation_finding_idx ON remediation (finding_id);
CREATE INDEX remediation_assignee_idx ON remediation (assignee_id, status);

-- Immutable verification record. This — not the remediation's status — is what
-- can move a finding to RESOLVED.
CREATE TABLE verification (
    id             text PRIMARY KEY,
    finding_id     text NOT NULL REFERENCES finding (id) ON DELETE CASCADE,
    remediation_id text REFERENCES remediation (id) ON DELETE SET NULL,
    outcome        verification_outcome NOT NULL,
    method         verification_method NOT NULL,
    verifier_id    text NOT NULL REFERENCES app_user (id),
    evidence_id    text REFERENCES evidence (id),
    notes          text NOT NULL DEFAULT '',
    verified_at    timestamptz NOT NULL DEFAULT now(),
    created_at     timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT verification_evidence_or_note CHECK (evidence_id IS NOT NULL OR btrim(notes) <> '')
);
CREATE INDEX verification_finding_idx ON verification (finding_id, verified_at DESC);
CREATE INDEX verification_remediation_idx ON verification (remediation_id);

ALTER TABLE finding_status_event
    ADD CONSTRAINT finding_status_event_verification_fk
    FOREIGN KEY (verification_id) REFERENCES verification (id);

ALTER TABLE model_version
    ADD CONSTRAINT model_version_training_dataset_fk
    FOREIGN KEY (training_dataset_version_id) REFERENCES dataset_version (id);

-- ---------------------------------------------------------------------------
-- Reports (immutable snapshot after generation)
-- ---------------------------------------------------------------------------
CREATE TABLE report (
    id            text PRIMARY KEY,
    project_id    text NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    job_id        text,
    title         text NOT NULL CHECK (btrim(title) <> ''),
    status        report_status NOT NULL DEFAULT 'DRAFT',
    snapshot_hash text,                            -- hash of the generated snapshot
    created_at    timestamptz NOT NULL DEFAULT now(),
    created_by    text NOT NULL REFERENCES app_user (id),
    published_at  timestamptz,
    CONSTRAINT report_job_same_project
        FOREIGN KEY (job_id, project_id) REFERENCES scan_job (id, project_id)
);
CREATE INDEX report_project_idx ON report (project_id, created_at DESC);

CREATE TABLE report_finding (
    report_id     text NOT NULL REFERENCES report (id) ON DELETE CASCADE,
    finding_id    text NOT NULL REFERENCES finding (id),
    position      integer NOT NULL CHECK (position >= 1),   -- deterministic export order
    severity      finding_severity NOT NULL,
    status        finding_status NOT NULL,
    title         text NOT NULL,
    target_name   text NOT NULL DEFAULT '',
    evidence_excerpt text NOT NULL DEFAULT '',
    PRIMARY KEY (report_id, finding_id),
    UNIQUE (report_id, position)
);

-- ---------------------------------------------------------------------------
-- Audit (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE audit_event (
    id            text PRIMARY KEY,
    occurred_at   timestamptz NOT NULL DEFAULT now(),
    actor_id      text REFERENCES app_user (id),
    actor_label   text NOT NULL,                   -- denormalized; survives user deletion
    action        text NOT NULL,                   -- "project.created", "finding.transitioned", …
    resource_type text NOT NULL,
    resource_id   text,
    resource_name text NOT NULL DEFAULT '',
    outcome       audit_outcome NOT NULL DEFAULT 'SUCCESS',
    request_id    text,
    metadata      jsonb NOT NULL DEFAULT '{}'::jsonb   -- redacted; no secrets/evidence bodies
);
CREATE INDEX audit_event_time_idx ON audit_event (occurred_at DESC);
CREATE INDEX audit_event_resource_idx ON audit_event (resource_type, resource_id);
CREATE INDEX audit_event_actor_idx ON audit_event (actor_id, occurred_at DESC);

-- Shared auth state (optional; enabled by SENTRIX_SHARED_AUTH=1)
CREATE TABLE revoked_token (
    fingerprint text PRIMARY KEY CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
    expires_at  timestamptz NOT NULL
);
CREATE INDEX revoked_token_expiry_idx ON revoked_token (expires_at);

CREATE TABLE rate_limit_bucket (
    bucket_key   text NOT NULL,
    window_start timestamptz NOT NULL,
    hits         integer NOT NULL CHECK (hits >= 0),
    PRIMARY KEY (bucket_key, window_start)
);

-- L3-C automation queue (policy/approval only; no execution credentials)
CREATE TABLE automation_candidate (
    id          text PRIMARY KEY,
    finding_id  text NOT NULL REFERENCES finding (id) ON DELETE CASCADE,
    target      text NOT NULL,
    action_code text NOT NULL,
    score       numeric(5,4) NOT NULL DEFAULT 0,
    status      text NOT NULL DEFAULT 'QUEUED'
                CHECK (status IN ('QUEUED', 'APPROVAL_REQUIRED', 'APPROVED', 'REJECTED', 'EXECUTED')),
    created_by  text REFERENCES app_user (id),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX automation_candidate_status_idx ON automation_candidate (status, score DESC);

CREATE TABLE automation_request (
    id           text PRIMARY KEY,
    candidate_id text NOT NULL REFERENCES automation_candidate (id) ON DELETE CASCADE,
    manifest     jsonb NOT NULL,
    status       text NOT NULL DEFAULT 'PENDING'
                 CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    requested_by text REFERENCES app_user (id),
    approved_by  text REFERENCES app_user (id),
    reason       text NOT NULL DEFAULT '',
    created_at   timestamptz NOT NULL DEFAULT now(),
    decided_at   timestamptz
);
CREATE INDEX automation_request_status_idx ON automation_request (status, created_at);

CREATE TABLE automation_execution (
    id            text PRIMARY KEY,
    candidate_id  text NOT NULL REFERENCES automation_candidate (id) ON DELETE CASCADE,
    request_id    text REFERENCES automation_request (id) ON DELETE SET NULL,
    action_code   text NOT NULL,
    target        text NOT NULL,
    status        text NOT NULL CHECK (status IN ('SUCCEEDED', 'FAILED', 'SNAPSHOT_MISMATCH')),
    before_hash   text,
    after_hash    text,
    http_status   integer,
    observations  jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_by    text REFERENCES app_user (id),
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX automation_execution_candidate_idx ON automation_execution (candidate_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Append-only enforcement
--   These tables are history: correction is append, never edit.
-- ---------------------------------------------------------------------------
CREATE FUNCTION sentrix_reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'append-only table % cannot be updated or deleted (% operation)', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$;

CREATE TRIGGER audit_event_append_only
    BEFORE UPDATE OR DELETE ON audit_event
    FOR EACH ROW EXECUTE FUNCTION sentrix_reject_mutation();

CREATE TRIGGER finding_status_event_append_only
    BEFORE UPDATE OR DELETE ON finding_status_event
    FOR EACH ROW EXECUTE FUNCTION sentrix_reject_mutation();

CREATE TRIGGER prompt_template_version_append_only
    BEFORE UPDATE OR DELETE ON prompt_template_version
    FOR EACH ROW EXECUTE FUNCTION sentrix_reject_mutation();

-- evidence / verification / report_finding are immutable through the API and
-- carry no UPDATE grant, but keep FK cascade (project/finding/report deletion
-- for retention or erasure) mechanically possible; see 07 D-14.

-- ---------------------------------------------------------------------------
-- Reference data (demo profiles — mirrors the three UI options)
-- ---------------------------------------------------------------------------
INSERT INTO scan_profile (id, name, adapter_code) VALUES
    ('external_attack_surface', 'External attack surface', 'demo'),
    ('api_authorization',       'API authorization',       'demo'),
    ('cloud_configuration',     'Cloud configuration',     'demo');

-- ---------------------------------------------------------------------------
-- Least privilege (run by ops, not by the app migration role)
--   The application role may read/insert but never UPDATE/DELETE append-only
--   tables; it may not run DDL. Migrations run as a separate role.
--   FK ON DELETE CASCADE actions are executed as the constraint owner, so the
--   retention/erasure path still works with the grants below.
-- ---------------------------------------------------------------------------
-- REVOKE UPDATE, DELETE ON audit_event, finding_status_event, evidence,
--     verification, report_finding FROM sentrix_app;
-- GRANT SELECT, INSERT ON audit_event, finding_status_event, evidence,
--     verification, report_finding TO sentrix_app;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO sentrix_readonly;

COMMIT;
