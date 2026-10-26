BEGIN;

CREATE TABLE artifact (
    sha256      text PRIMARY KEY CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    project_id  text NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    evidence_id text REFERENCES evidence (id) ON DELETE SET NULL,
    created_by  text NOT NULL REFERENCES app_user (id),
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX artifact_project_idx ON artifact (project_id);

GRANT SELECT, INSERT ON artifact TO sentrix_app;

COMMIT;
