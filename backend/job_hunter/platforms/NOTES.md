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
