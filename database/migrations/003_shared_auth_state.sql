BEGIN;

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

GRANT SELECT, INSERT, UPDATE, DELETE ON revoked_token TO sentrix_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON rate_limit_bucket TO sentrix_app;

COMMIT;
