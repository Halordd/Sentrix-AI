-- M7 evaluation writer role. Run as a role that can create roles (usually postgres):
--   sudo -u postgres psql -d sentrix -f 002_evaluation_role.sql
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
