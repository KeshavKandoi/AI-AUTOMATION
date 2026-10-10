-- Run once in Supabase after deploying the release that removes the integration.
-- Deletes retired OAuth credentials while preserving historical task/audit data.
BEGIN;
DELETE FROM oauth_tokens
WHERE integration_id IN (SELECT id FROM integrations WHERE provider = 'calendar');
DELETE FROM integrations WHERE provider = 'calendar';
COMMIT;
