# WorkForge (AI-AUTOMATION)

WorkForge is an automation dashboard for GitHub activity, task approval, workflows, scheduled commits and emails, job tracking, and audit logs. The React/Vite frontend calls a FastAPI backend. Supabase stores users, organizations, integrations, jobs, and OAuth tokens; APScheduler runs background jobs. Google Gemini helps generate task suggestions. OAuth tokens are encrypted before storage.

## Local setup

1. Use Node.js 22 and Python 3.12 or later. Start a Supabase project with the tables expected by `backend/` and obtain its URL, anon key, service-role key, and JWT secret. This repository does not include database migrations, so an existing compatible Supabase schema is required.
2. Copy `backend/.env.example` to `backend/.env` and replace placeholders. The complete backend variable list and optional scheduler/rate-limit settings are documented in that example. Generate `TOKEN_ENCRYPTION_KEY` with `cryptography.fernet.Fernet.generate_key()`; keep the value stable across restarts.
3. Copy `ai-coo-frontend/.env.example` to `ai-coo-frontend/.env` and set `VITE_API_BASE_URL=http://127.0.0.1:8000`.

Required backend variables are `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI`, `GITHUB_WEBHOOK_SECRET`, `GENERIC_WEBHOOK_SECRET`, `GEMINI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_GMAIL_REDIRECT_URI`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and `TOKEN_ENCRYPTION_KEY`. `RENDER_BASE_URL` must be an HTTPS public backend URL before connecting a GitHub repository. The example file documents every optional variable.

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

## Google OAuth and Gmail

Create a Google Cloud OAuth web client. Configure the consent screen and register the exact redirect URI in `GOOGLE_GMAIL_REDIRECT_URI`, such as `http://127.0.0.1:8000/gmail/callback` locally and the deployed backend callback in production. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. The Gmail connection requests exactly:

- `https://www.googleapis.com/auth/gmail.send`
- `https://www.googleapis.com/auth/userinfo.email`

Gmail is used to send user-configured workflow or scheduled emails and approved task emails. The application does not read Gmail inbox messages, list messages, or modify mailbox state. A human approval is required for task email sends; workflow and scheduled sends follow the user's saved configuration. Tokens are encrypted at rest and scoped to an organization. Disconnecting an integration deletes its stored tokens. Keep the client secret, Resend key, Supabase service key, JWT secret, and encryption key out of version control.

## Deployment

Deploy `backend/` as a Python service (for example, Render) with `uvicorn main:app --host 0.0.0.0 --port $PORT`. Provide the backend variables from `.env.example` as deployment secrets, set `ENVIRONMENT=production`, set `ALLOWED_ORIGINS` to the exact HTTPS frontend origin, and use HTTPS callback URLs in the GitHub and Google consoles. Production refresh cookies use `Secure` and `SameSite=None`; local HTTP uses `SameSite=Lax` without `Secure`. Deploy `ai-coo-frontend/` as a Vite static site with `npm ci && npm run build`, publish `dist/`, and set `VITE_API_BASE_URL` to the backend HTTPS URL. The existing `vercel.json` supports SPA routing.

Before deploying this removal, run `backend/migrations/retire_calendar_integration.sql` against Supabase to delete any previously stored Google Calendar OAuth credentials. The application no longer requests or uses that permission.

Optional legacy scheduler jobs only run when `SCHEDULER_ORG_ID` and `SCHEDULER_REPOSITORY` are explicitly configured and the organization has a connected GitHub integration. `SCHEDULER_SELF_URL` enables keep-alive pings. In production, also set `SCHEDULER_ENABLE_PRODUCTION=true` after verifying the target. Keep test organizations and repositories out of production configuration.
