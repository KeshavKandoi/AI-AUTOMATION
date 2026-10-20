-- Run this on the WorkForge Supabase project before connecting Discord.
-- Keep the existing OAuth providers while admitting Discord state records.
BEGIN;

ALTER TABLE public.oauth_states
  DROP CONSTRAINT IF EXISTS oauth_states_provider_check;

ALTER TABLE public.oauth_states
  ADD CONSTRAINT oauth_states_provider_check
  CHECK (provider IN ('github', 'gmail', 'calendar', 'discord'));

COMMIT;
