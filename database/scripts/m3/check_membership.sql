SELECT project_id, user_id, role FROM project_member ORDER BY project_id, user_id;

SELECT id, action, resource_id FROM audit_event WHERE action LIKE 'membership.%' ORDER BY occurred_at;
