ALTER TABLE finding_status_event DISABLE TRIGGER USER;
ALTER TABLE audit_event DISABLE TRIGGER USER;

DELETE FROM finding_status_event WHERE id = 'fse-8598a552de5d';
DELETE FROM audit_event WHERE id = 'audit-4bc64bd9256a';

ALTER TABLE finding_status_event ENABLE TRIGGER USER;
ALTER TABLE audit_event ENABLE TRIGGER USER;

UPDATE finding
SET status = 'CONFIRMED',
    updated_at = '2026-10-18T02:43:00Z',
    resolved_at = NULL
WHERE id = 'finding-bola';

SELECT (SELECT count(*) FROM finding_status_event) events,
       (SELECT count(*) FROM audit_event) audits;
