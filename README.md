# WorkForge

WorkForge automates work from GitHub events and scheduled jobs. A React/Vite frontend calls a FastAPI backend. Supabase stores accounts, organization data, and encrypted OAuth tokens. Background jobs run inside the backend process.

## Setup

Use Node.js 22+ and Python 3.12+. Supply an existing Supabase project with the tables used by the backend. Copy backend/.env.example to backend/.env and ai-coo-frontend/.env.example to ai-coo-frontend/.env, then replace required placeholders. The backend example lists supported variables. Generate TOKEN_ENCRYPTION_KEY with cryptography.fernet.Fernet.generate_key() and keep it stable. Never commit .env files.

Required backend settings are the Supabase URL, anon key, service role key, and JWT secret; GitHub client ID, client secret, redirect URI, and webhook secret; Google client ID, client secret, and Gmail and Calendar redirect URIs; the Gemini API key; Resend API key and verified sender address; GENERIC_WEBHOOK_SECRET; and TOKEN_ENCRYPTION_KEY. Set ALLOWED_ORIGINS to the frontend origin and FRONTEND_URL to that same origin so browser OAuth callbacks return to WorkForge. RENDER_BASE_URL is required to register GitHub repository webhooks. Optional scheduler, rate limit, cookie, and Discord settings are listed in backend/.env.example.

    cd backend
    python -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt pytest
    uvicorn main:app --reload --host 127.0.0.1 --port 8000

    cd ai-coo-frontend
    npm ci
    npm run dev -- --host 127.0.0.1

Set VITE_API_BASE_URL=http://127.0.0.1:8000 locally. Use 127.0.0.1 for both frontend and backend so the local HTTP refresh cookie stays same-site.

## Integrations

Enable the Gmail and Calendar APIs in Google Cloud, configure an OAuth consent screen, and register GOOGLE_GMAIL_REDIRECT_URI and GOOGLE_CALENDAR_REDIRECT_URI with the Google OAuth web client. Gmail requests exactly https://www.googleapis.com/auth/gmail.send and https://www.googleapis.com/auth/userinfo.email. It sends workflow, scheduled, and approved task emails; it never reads the inbox. Calendar connects separately with https://www.googleapis.com/auth/calendar to list and create events. OAuth tokens are encrypted at rest per organization.

Calendar has no AI summary feature; the retired /calendar/summary endpoint returns 404. Event listing, creation, and lunch-block automation do not send Calendar data to the AI provider. GitHub summaries, pull-request summaries, and task suggestions still use AI; the task planner includes saved memory context.

Connect GitHub from WorkForge and select a repository. The backend registers POST /webhooks/github using an organization-specific secret. Configure GitHub to deliver push, issues, and pull_request. Verified push events run matching active workflows immediately; a send_email action sends during webhook processing. Scheduled email jobs run when due, checked about once per minute. Workflow actions run automatically when their trigger and conditions match; the task approval email action requires human approval. Webhook deliveries are deduplicated by organization and event key.

Discord is configured in Integrations, without OAuth. Paste a Discord HTTPS webhook URL into its Configure dialog. The backend validates it, stores it for the authenticated organization, and returns only a masked status. A saved organization URL takes precedence over the optional environment fallback. Disconnect removes the saved URL; if an environment fallback applies, it becomes active again. An environment-managed URL cannot be removed from the UI.

For one Render environment URL, set both DISCORD_WEBHOOK_URL and DISCORD_ENV_ORG_ID on the backend service, then restart it. The fallback works only for that exact organization ID. An operator can obtain the ID from the Supabase dashboard SQL editor using the verified account email:

    SELECT organization_id FROM public.user_profiles WHERE email = 'operator@example.com';

Confirm the matching organization before saving the Render variables. Remove both variables and restart the backend to disconnect an environment-managed webhook. Integrations shows the effective source. Connected means a valid URL is configured; it does not confirm live delivery.

## Deployment and operations

Deploy backend/ as one always-on process with uvicorn main:app --host 0.0.0.0 --port $PORT. Run one worker and one replica while schedulers run in-process. Set ENVIRONMENT=production, ALLOWED_ORIGINS to the exact HTTPS frontend origin, RENDER_BASE_URL to the HTTPS backend URL, and HTTPS OAuth callback URLs in the GitHub and Google consoles. Deploy ai-coo-frontend/ as a Vite static app with npm ci && npm run build, publish dist/, and set VITE_API_BASE_URL to the backend HTTPS URL. Production refresh cookies use Secure and SameSite=None; local HTTP uses SameSite=Lax without Secure.

The backend must be awake to receive webhooks and run scheduled jobs. If it sleeps, webhook delivery can fail and due jobs wait until it resumes. Legacy scheduler jobs require SCHEDULER_ORG_ID and SCHEDULER_REPOSITORY; production also requires SCHEDULER_ENABLE_PRODUCTION=true. Review those targets before enabling them. The repository assumes a compatible Supabase schema; review historical migrations before running any against existing data.

Account deletion checks the current password and organization membership. Sole-member deletion removes organization jobs, data, and stored integration tokens. Deletion from a shared organization leaves shared resources for other members. Supabase Auth and database cleanup cannot share one transaction, so a partial failure requires operator review. The UI reports failure and does not treat it as a completed deletion.

## Security and tests

Keep service role keys, OAuth secrets, webhook URLs, Resend keys, and encryption keys in secret settings. Discord status responses expose only a fixed mask and configuration source. Backend authorization still uses organization IDs after they are hidden from Settings.

    cd backend
    python -m pytest -q

    cd ai-coo-frontend
    npm run lint
    npm run build

Tests mock external services and do not require production secrets. Use disposable accounts for any live password or account deletion check. Never run account deletion against an active account.
