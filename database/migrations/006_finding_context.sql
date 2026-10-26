BEGIN;

ALTER TABLE finding
    ADD COLUMN IF NOT EXISTS cwe text,
    ADD COLUMN IF NOT EXISTS location jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMIT;
