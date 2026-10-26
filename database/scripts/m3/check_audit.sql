SELECT id, action, resource_id, outcome
FROM audit_event
WHERE resource_id = 'finding-bola'
ORDER BY occurred_at DESC;

SELECT id, from_status, to_status
FROM finding_status_event
WHERE finding_id = 'finding-bola'
ORDER BY occurred_at DESC;
