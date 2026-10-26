ALTER TABLE finding_status_event DISABLE TRIGGER USER;

DELETE FROM finding_status_event
WHERE finding_id = 'finding-bola'
  AND from_status = 'CONFIRMED'
  AND to_status = 'IN_PROGRESS';

ALTER TABLE finding_status_event ENABLE TRIGGER USER;

UPDATE finding
SET status = 'CONFIRMED',
    updated_at = '2026-10-18T02:43:00Z'
WHERE id = 'finding-bola';
