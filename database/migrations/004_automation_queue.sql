BEGIN;

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

GRANT SELECT, INSERT, UPDATE ON automation_candidate, automation_request TO sentrix_app;

COMMIT;
