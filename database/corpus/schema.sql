BEGIN;

CREATE SCHEMA IF NOT EXISTS corpus_pilot AUTHORIZATION sentrix_migrator;

CREATE TABLE IF NOT EXISTS corpus_pilot.project (
    id          text PRIMARY KEY,
    name        text NOT NULL,
    status      text NOT NULL DEFAULT 'ACTIVE',
    scope       text NOT NULL DEFAULT '',
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS corpus_pilot.target (
    id          text PRIMARY KEY,
    project_id  text NOT NULL REFERENCES corpus_pilot.project (id) ON DELETE CASCADE,
    name        text NOT NULL,
    type        text NOT NULL,
    scope       text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS corpus_pilot.finding (
    id          text PRIMARY KEY,
    project_id  text NOT NULL REFERENCES corpus_pilot.project (id) ON DELETE CASCADE,
    target_id   text NOT NULL REFERENCES corpus_pilot.target (id) ON DELETE CASCADE,
    source_id   text NOT NULL UNIQUE,
    title       text NOT NULL,
    severity    text NOT NULL,
    status      text NOT NULL DEFAULT 'NEW',
    cwe         text,
    location    jsonb NOT NULL DEFAULT '{}'::jsonb,
    verified    boolean NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS corpus_pilot.candidate (
    id           text PRIMARY KEY,
    finding_id   text NOT NULL REFERENCES corpus_pilot.finding (id) ON DELETE CASCADE,
    target       text NOT NULL,
    action_code  text NOT NULL,
    score        numeric(5,4) NOT NULL,
    status       text NOT NULL DEFAULT 'QUEUED',
    model        text NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS corpus_finding_target_idx ON corpus_pilot.finding (target_id);
CREATE INDEX IF NOT EXISTS corpus_candidate_score_idx ON corpus_pilot.candidate (status, score DESC);

COMMIT;
