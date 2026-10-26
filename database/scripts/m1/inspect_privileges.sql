\pset pager off
\pset format aligned

SELECT 'default_acl' AS section;
SELECT defaclrole::regrole AS grantor,
       COALESCE(defaclnamespace::regnamespace::text, '<all>') AS schema,
       defaclobjtype AS objtype,
       defaclacl AS acl
FROM pg_default_acl
ORDER BY 1,2,3;

SELECT 'append_only_privileges' AS section;
SELECT c.relname,
       has_table_privilege('sentrix_app', c.oid, 'SELECT') AS can_select,
       has_table_privilege('sentrix_app', c.oid, 'INSERT') AS can_insert,
       has_table_privilege('sentrix_app', c.oid, 'UPDATE') AS can_update,
       has_table_privilege('sentrix_app', c.oid, 'DELETE') AS can_delete,
       has_table_privilege('sentrix_app', c.oid, 'TRUNCATE') AS can_truncate
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN ('audit_event','finding_status_event','prompt_template_version','evidence','verification','report_finding')
ORDER BY c.relname;

SELECT 'app_table_privileges' AS section;
SELECT c.relname,
       has_table_privilege('sentrix_app', c.oid, 'SELECT') AS sel,
       has_table_privilege('sentrix_app', c.oid, 'INSERT') AS ins,
       has_table_privilege('sentrix_app', c.oid, 'UPDATE') AS upd,
       has_table_privilege('sentrix_app', c.oid, 'DELETE') AS del
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname;
