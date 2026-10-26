ALTER TABLE finding_status_event DISABLE TRIGGER USER;
DELETE FROM finding_status_event WHERE finding_id = 'finding-47bbbfe9d20f';
ALTER TABLE finding_status_event ENABLE TRIGGER USER;

DELETE FROM evidence WHERE finding_id = 'finding-47bbbfe9d20f';
DELETE FROM finding WHERE id = 'finding-47bbbfe9d20f';
DELETE FROM scan_run WHERE job_id = 'scan-fda6bdc6d02d';
DELETE FROM scan_job WHERE id = 'scan-fda6bdc6d02d';

SELECT (SELECT count(*) FROM scan_job) scans,
       (SELECT count(*) FROM scan_run) runs,
       (SELECT count(*) FROM finding) findings,
       (SELECT count(*) FROM evidence) evidence,
       (SELECT count(*) FROM finding_status_event) events;
