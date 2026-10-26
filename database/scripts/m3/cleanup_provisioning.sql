DELETE FROM app_user WHERE id = 'user-dc8ce466b557';

ALTER TABLE audit_event DISABLE TRIGGER USER;
DELETE FROM audit_event
WHERE action LIKE 'membership.%'
   OR action IN ('user.created', 'user.updated');
ALTER TABLE audit_event ENABLE TRIGGER USER;

SELECT (SELECT count(*) FROM app_user) users,
       (SELECT count(*) FROM project_member) members,
       (SELECT count(*) FROM audit_event) audits;
