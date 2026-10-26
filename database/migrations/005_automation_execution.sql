BEGIN;

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

GRANT SELECT, INSERT ON automation_execution TO sentrix_app;

COMMIT;
