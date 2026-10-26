SELECT has_schema_privilege('sentrix_app', 'public', 'CREATE') AS app_can_create,
       has_schema_privilege('sentrix_app', 'public', 'USAGE') AS app_can_use;
