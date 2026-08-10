# Provider Notes

## Indeed — not implemented (2026-08-08 investigation)

Indeed was investigated as a Playwright-based provider and found unsuitable
for reliable production use with this architecture.

**Finding:** A single request against indeed.com/jobs returns real, valid
job listings via plain headless Playwright. However, a second request
shortly after (same session, ~1.5s apart) returns a Cloudflare
"Just a moment..." challenge page with zero job cards — confirmed via
live testing, not assumption. This means Indeed cannot be trusted for a
6-hourly scheduled sweep across multiple role searches per org: it would
appear to work in isolated testing and then silently degrade to 0 results
in production the moment Cloudflare's per-session/per-IP heuristics
trigger, which is worse than not having the provider at all (false
confidence with no visible failure).

**Explicitly not pursued:** stealth browser fingerprinting, residential
proxy rotation, CAPTCHA solving services, or other anti-bot evasion. These
are real techniques other tools use, but they're an ongoing arms race with
real infrastructure cost, and reliability still isn't guaranteed even with
them — not a foundation for a dependable feature.

**Path forward if revisited:** Indeed has an official Publisher/employer
API program requiring partnership approval — that's the legitimate path,
not scraping. No action taken on this since it requires external approval
outside this system's control.

**Current state:** Indeed is NOT registered in the provider registry.
No `job_hunter/platforms/indeed.py` exists. This is intentional, not an
oversight.

## X (Twitter) — not implemented (2026-08-10 investigation)

**Official API:** A legitimate, working API exists for this use case
(`GET /2/tweets/search/recent`) — architecturally the right tool, unlike
LinkedIn. However, as of Feb 2026 X moved to pure pay-per-use billing with
no free tier and no subscription option: $0.005/post read, $0.010/user
read, requires a funded developer account (credit card, pre-purchased
credits) before any request succeeds. This is a real ongoing operating
cost with every 6-hourly sweep across every org, not a one-time setup
cost — a business decision, not an engineering one.

**Playwright (tested live, 2026-08-10):** Immediate, unconditional login
wall on the very first request — no public/logged-out search access
exists at all (confirmed: x.com/search redirected straight to
/i/jf/onboarding/web?...mode=login with zero content visible). This is a
harder block than both Indeed (intermittent Cloudflare, ~2 requests) and
LinkedIn (partial public access, ~2/3 of requests succeeded) — there is
no unauthenticated path whatsoever. The only technical workaround would
require maintaining a real logged-in account's session, which is a
genuine account-based access-control bypass, not browser fingerprint
evasion — explicitly outside what this system will do.

**Decision: not implemented.** Blocked on two independent grounds: (1)
Playwright is definitively not viable (confirmed via live test, not
assumption), (2) the only remaining path (official API) requires a
funded account and ongoing real cost that only the product owner can
authorize.

**Path forward if revisited:** requires (a) a funded X Developer account
with billing attached, and (b) a Bearer Token stored via new credential
infrastructure (not the existing OAuth-refresh pattern, since X's
pay-per-use API uses App-level Bearer Tokens, not per-user OAuth) — a
scoped, well-understood addition if/when the cost is approved.

**Current state:** X is NOT registered in the provider registry. No
`job_hunter/platforms/x.py` exists. This is intentional, not an
oversight.
