BEGIN;

-- Application role must not mutate append-only or immutable records.
REVOKE UPDATE, DELETE ON
    audit_event,
    finding_status_event,
    prompt_template_version,
    evidence,
    verification,
    report_finding
FROM sentrix_app;

-- MVP has no delete endpoints; remove DELETE from every table.
REVOKE DELETE ON ALL TABLES IN SCHEMA public FROM sentrix_app;

-- Future tables must be granted explicitly by migrations, not blanket defaults.
ALTER DEFAULT PRIVILEGES FOR ROLE sentrix_migrator IN SCHEMA public
    REVOKE ALL ON TABLES FROM sentrix_app;

COMMIT;
