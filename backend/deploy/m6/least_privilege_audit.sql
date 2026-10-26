-- M6-06 least-privilege audit for sentrix_app.
SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'sentrix_app'
ORDER BY table_name, privilege_type;

SELECT has_schema_privilege('sentrix_app', 'public', 'CREATE') AS app_can_create_schema,
       has_schema_privilege('sentrix_app', 'public', 'USAGE') AS app_can_use_schema;

SELECT table_name, privilege_type
FROM information_schema.role_table_grants
WHERE grantee = 'sentrix_app'
  AND privilege_type IN ('DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER')
ORDER BY table_name, privilege_type;
