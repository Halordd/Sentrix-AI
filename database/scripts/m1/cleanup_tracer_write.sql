ALTER TABLE finding_status_event DISABLE TRIGGER USER;
ALTER TABLE finding DISABLE TRIGGER USER;
ALTER TABLE scan_job DISABLE TRIGGER USER;

DELETE FROM finding_status_event
WHERE finding_id IN (SELECT id FROM finding WHERE target_id = 'target-b9cbcc487413');
DELETE FROM finding WHERE target_id = 'target-b9cbcc487413';
DELETE FROM scan_job WHERE id = 'scan-f7dee18907a9';
DELETE FROM target_authorization WHERE target_id = 'target-b9cbcc487413';
DELETE FROM target WHERE id = 'target-b9cbcc487413';

ALTER TABLE finding_status_event ENABLE TRIGGER USER;
ALTER TABLE finding ENABLE TRIGGER USER;
ALTER TABLE scan_job ENABLE TRIGGER USER;
