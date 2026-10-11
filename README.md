# WorkForge (AI-AUTOMATION)

WorkForge is an automation dashboard for GitHub activity, task approval, workflows, scheduled commits and emails, Google Calendar, job tracking, and audit logs. The React/Vite frontend calls a FastAPI backend. Supabase stores users, organizations, integrations, jobs, and encrypted OAuth tokens; APScheduler runs background jobs. Google Gemini helps generate task suggestions and calendar summaries.

## Local setup

1. Use Node.js 22 and Python 3.12 or later. Start a Supabase project with the tables expected by `backend/` and obtain its URL, anon key, service-role key, and JWT secret. This repository does not include database migrations, so an existing compatible Supabase schema is required.
2. Copy `backend/.env.example` to `backend/.env` and replace placeholders. The complete backend variable list and optional scheduler/rate-limit settings are documented in that example. Generate `TOKEN_ENCRYPTION_KEY` with `cryptography.fernet.Fernet.generate_key()`; keep the value stable across restarts.
3. Copy `ai-coo-frontend/.env.example` to `ai-coo-frontend/.env` and set `VITE_API_BASE_URL=http://127.0.0.1:8000`.

Required backend variables are `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`, `GITHUB_WEBHOOK_SECRET`, `GENERIC_WEBHOOK_SECRET`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_GMAIL_REDIRECT_URI`, `GOOGLE_CALENDAR_REDIRECT_URI`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and `TOKEN_ENCRYPTION_KEY`. `RENDER_BASE_URL` must be an HTTPS public backend URL before connecting a GitHub repository. The example file documents every optional variable.

```sh
cd backend
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt pytest
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

```sh
cd ai-coo-frontend
npm ci
npm run dev -- --host 127.0.0.1
```

The frontend is at `http://127.0.0.1:5173`; use that hostname with the example backend URL so the HTTP refresh cookie remains same-site. Run `npm run lint`, `npm run build`, and `cd backend && python -m pytest -q` before a release. Backend tests use placeholder configuration and do not require production secrets.

## Google OAuth, Gmail, and Calendar

Enable the Gmail API and Google Calendar API in the Google Cloud project, then create a web OAuth client. Configure the consent screen and register both callback URIs: `GOOGLE_GMAIL_REDIRECT_URI` (for example, `http://127.0.0.1:8000/gmail/callback`) and `GOOGLE_CALENDAR_REDIRECT_URI` (for example, `http://127.0.0.1:8000/calendar/callback`). Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. Gmail requests exactly these two scopes:

- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/userinfo.email`

Gmail sends user-configured workflow or scheduled emails and approved task emails. The application only sends messages; it does not read inbox messages, list messages, or modify mailbox state. Task email sends require human approval in the task approval flow. A saved active workflow that includes `send_email` sends automatically once its trigger and conditions match; there is no per-event approval step. Scheduled email jobs use APScheduler. Tokens are encrypted at rest and scoped to an organization. Disconnecting an integration deletes its stored tokens. Keep client secrets, the Resend key, Supabase service key, JWT secret, and encryption key out of version control.

The separate Calendar connection requests `https://www.googleapis.com/auth/calendar`. It lists the next ten upcoming events, generates an AI summary, creates events requested by the user, and supports approval-gated task event creation. Calendar integration settings and the calendar page are available after sign-in. Calendar tokens are stored encrypted per organization.

Calendar uses its own OAuth authorization request and requires the Calendar API enabled in Google Cloud. The Calendar page provides connect, refresh, event listing, summary, and event creation controls. The integration is labeled Production in the UI. Keep `GOOGLE_CALENDAR_REDIRECT_URI` configured alongside the Gmail callback URI.

## GitHub workflow email timing

Connect GitHub and select a repository in the GitHub integration page. The backend registers a webhook at `https://<backend-host>/webhooks/github` using the organization's generated webhook secret. Authorize the GitHub OAuth token with repository and webhook administration access. GitHub should deliver `push`, `issues`, and `pull_request`; WorkForge maps pushes to the `push` workflow trigger, `issues.opened` to `issue_created`, and `pull_request.opened` to `pull_request_opened`.

A push webhook is verified and dispatched synchronously. Matching active workflows run immediately in the webhook request; a matching `send_email` action sends the Gmail message in that request, rather than creating a scheduled email job. The Commit Scheduler also dispatches a push workflow immediately after its commit succeeds. Separate scheduled email jobs are checked every minute and run once the configured `send_time` is reached (default 09:00); `send_time` is interpreted in Asia/Kolkata (IST), so scheduler delay is up to about one minute while the backend is running. APScheduler is in-process, so the backend must be awake for webhook execution and background schedules. Run one backend replica with one worker while using these schedulers; separate worker processes do not share a scheduler lock. If the service sleeps, webhook delivery can fail or be retried by GitHub, and scheduled work waits until the service runs again.

Workflows are selected by organization, trigger type, and active status. Conditions compare event fields such as repository, branch, commit author, and commit message using the configured AND/OR logic. The event is deduplicated by organization, repository, trigger type, and event key before workflow execution. A failed send is recorded as a partial-failure run and in audit logs; the deduplication claim prevents webhook redelivery from automatically sending the same event again. A failed scheduled email is recorded and is not retried automatically that day; an authorized user can use the job's Run Now action to retry. An active workflow's email action is automatic as described above; users who need per-message approval should use the task approval email action instead.

The GitHub webhook endpoint is `POST /webhooks/github`. Configure the repository webhook for `push`, `issues`, and `pull_request` events, with the secret generated for the connected organization. GitHub signs the raw payload with HMAC SHA-256; WorkForge resolves the organization by matching the signature against stored secrets for that repository. A verified event is dispatched directly to the workflow engine and returns without invoking the unrelated general-purpose orchestrator. Manual workflow Run Now executes the same condition and action engine against sample context; workflows must be active and unexpired. Repositories shown for connection are fetched from the authenticated GitHub account across all API pages, and only those repositories can be selected.

## Discord notifications

Discord workflow actions use an organization-specific `organizations.discord_webhook_url`. Configure that URL through your organization administration process; it contains the webhook credential and must be treated as a secret. `DISCORD_WEBHOOK_URL` is an optional development fallback restricted to `TEST_ORG_ID` outside production; it is not required for startup, Gmail, Calendar, or GitHub. Discord webhook URLs are host/path validated, and the URL is not returned in API responses or written to logs. Discord webhooks do not use a separate bot API key in this integration.


## Deployment

Deploy `backend/` as a Python service (for example, Render) with `uvicorn main:app --host 0.0.0.0 --port $PORT`. Provide the backend variables from `.env.example` as deployment secrets, set `ENVIRONMENT=production`, set `ALLOWED_ORIGINS` to the exact HTTPS frontend origin, and use HTTPS callback URLs in the GitHub and Google consoles. Production refresh cookies use `Secure` and `SameSite=None`; local HTTP uses `SameSite=Lax` without `Secure`. Deploy `ai-coo-frontend/` as a Vite static site with `npm ci && npm run build`, publish `dist/`, and set `VITE_API_BASE_URL` to the backend HTTPS URL. The existing `vercel.json` supports SPA routing.

The repository assumes an existing compatible Supabase schema, including the Calendar integration tables used by your deployment. No destructive data migration is part of Calendar restoration.

Optional legacy scheduler jobs only run when `SCHEDULER_ORG_ID` and `SCHEDULER_REPOSITORY` are explicitly configured and the organization has a connected GitHub integration. `SCHEDULER_SELF_URL` enables keep-alive pings. In production, also set `SCHEDULER_ENABLE_PRODUCTION=true` after verifying the target. Keep test organizations and repositories out of production configuration.
