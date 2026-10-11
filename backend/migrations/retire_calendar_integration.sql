-- Manual, idempotent deployment step. Never run from application startup.
-- Only oauth_tokens and integrations rows for the retired provider are deleted.
-- Historical tasks and audit_logs are preserved.
BEGIN;
DELETE FROM oauth_tokens
WHERE integration_id IN (SELECT id FROM integrations WHERE provider = 'calendar');
DELETE FROM integrations WHERE provider = 'calendar';
COMMIT;
