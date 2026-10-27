BEGIN;

ALTER TABLE corpus_pilot.candidate
    ALTER COLUMN score TYPE numeric(7,6);

COMMIT;
