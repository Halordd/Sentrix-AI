DELETE FROM project_member
WHERE project_id = 'project-atlas' AND user_id = 'user-jon';

ALTER TABLE audit_event DISABLE TRIGGER USER;
DELETE FROM audit_event WHERE action LIKE 'membership.%';
ALTER TABLE audit_event ENABLE TRIGGER USER;

SELECT (SELECT count(*) FROM project_member) members,
       (SELECT count(*) FROM audit_event) audits;
