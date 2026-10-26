\pset pager off
\pset format aligned

SELECT 'public_tables' AS metric, count(*)::text AS value
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname = 'public';

SELECT 'public_enums' AS metric, count(*)::text AS value
FROM pg_type t
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE t.typtype = 'e' AND n.nspname = 'public';

SELECT 'non_internal_triggers' AS metric, count(*)::text AS value
FROM pg_trigger
WHERE NOT tgisinternal;

SELECT 'table_owners' AS metric, string_agg(DISTINCT pg_get_userbyid(c.relowner), ', ') AS value
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname = 'public';

SELECT 'seed_scan_profiles' AS metric, count(*)::text AS value
FROM scan_profile;

SELECT 'app_schema_usage' AS metric,
       has_schema_privilege('sentrix_app', 'public', 'USAGE')::text AS value;

SELECT 'app_select_finding' AS metric,
       has_table_privilege('sentrix_app', 'finding', 'SELECT')::text AS value;

SELECT 'app_update_audit' AS metric,
       has_table_privilege('sentrix_app', 'audit_event', 'UPDATE')::text AS value;
