#!/usr/bin/env bash
# Run on VM02 (database host) as a user with sudo.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "run with sudo on VM02" >&2
  exit 2
fi

sudo -u postgres psql -d sentrix <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sentrix_eval') THEN
        CREATE ROLE sentrix_eval NOLOGIN;
    END IF;
END
$$;
GRANT CONNECT ON DATABASE sentrix TO sentrix_eval;
GRANT USAGE ON SCHEMA public TO sentrix_eval;
GRANT SELECT ON app_user, model, model_version, dataset, dataset_version TO sentrix_eval;
GRANT INSERT ON model, model_version, dataset, dataset_version, evaluation_run TO sentrix_eval;
GRANT SELECT ON evaluation_run TO sentrix_eval;
GRANT UPDATE (stage, promoted_at) ON model_version TO sentrix_eval;
GRANT sentrix_eval TO sentrix_migrator;
SQL

echo "sentrix_eval role installed on VM02"
