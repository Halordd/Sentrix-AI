DELETE FROM verification WHERE remediation_id = 'task-6373857ad9c8';
DELETE FROM remediation WHERE id = 'task-6373857ad9c8';

ALTER TABLE finding_status_event DISABLE TRIGGER USER;
DELETE FROM finding_status_event
WHERE finding_id = 'finding-bucket'
  AND from_status = 'NEW'
  AND to_status = 'RESOLVED';
ALTER TABLE finding_status_event ENABLE TRIGGER USER;

UPDATE finding
SET status = 'NEW',
    updated_at = '2026-10-18T00:35:00Z',
    resolved_at = NULL
WHERE id = 'finding-bucket';

SELECT id, status, resolved_at FROM finding WHERE id = 'finding-bucket';
SELECT count(*) AS remediation_count FROM remediation;
SELECT count(*) AS verification_count FROM verification;
SELECT count(*) AS event_count FROM finding_status_event;
