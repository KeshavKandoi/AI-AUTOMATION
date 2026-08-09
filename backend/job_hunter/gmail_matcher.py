"""
Confidence-scoring matcher: given a classified recruitment email, finds
which (if any) of the org's job_hunter_applications it belongs to.

Deliberately conservative — a wrong high-confidence match would corrupt
a real application's status, which is worse than leaving an email
unmatched for manual review. See MATCH_THRESHOLD and per-signal weights
below; no single signal can cross the threshold alone, requiring genuine
multi-signal corroboration before an automatic status update happens.
"""
import re
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

MATCH_THRESHOLD = 70

WEIGHT_VERIFIED_DOMAIN = 40
WEIGHT_GUESSED_DOMAIN = 15   # capped low — heuristic only, never decisive alone
WEIGHT_COMPANY_NAME = 25
WEIGHT_JOB_TITLE = 20
WEIGHT_RECIPIENT_EMAIL = 10
WEIGHT_RECENCY = 5

RECENCY_WINDOW_DAYS = 60


@dataclass
class MatchResult:
    application_id: Optional[str]
    score: float
    signals: dict = field(default_factory=dict)   # {signal_name: points_awarded}
    is_confident: bool = False


def _extract_sender_domain(sender_email: str) -> Optional[str]:
    match = re.search(r"@([a-zA-Z0-9.-]+)", sender_email or "")
    return match.group(1).lower() if match else None


def _guess_domain_from_company(company_name: str) -> Optional[str]:
    """Best-effort only. Strips common suffixes (Inc, Corp, LLC, Ltd) and
    whitespace, lowercases, appends .com. This is frequently wrong (many
    companies don't use their exact name as their domain) — hence the
    low weight when used as a signal."""
    if not company_name:
        return None
    name = re.sub(r"\b(inc|corp|corporation|llc|ltd|limited|co)\b\.?", "", company_name, flags=re.IGNORECASE)
    name = re.sub(r"[^a-zA-Z0-9]", "", name).lower().strip()
    return f"{name}.com" if name else None


def _contains_word(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    pattern = r"\b" + re.escape(needle) + r"\b"
    return re.search(pattern, haystack, re.IGNORECASE) is not None


def _is_recent(applied_at: Optional[str], created_at: str) -> bool:
    timestamp_str = applied_at or created_at
    if not timestamp_str:
        return False
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts) <= timedelta(days=RECENCY_WINDOW_DAYS)
    except (ValueError, TypeError):
        return False


def score_application_match(
    sender_email: str,
    subject: str,
    body_snippet: str,
    recipient_email: str,
    onboarding_email: str,
    application: dict,
    job: dict,
    verified_domain: Optional[str],
) -> MatchResult:
    """
    Scores a single (application, job) pair against one email. Caller
    (gmail_integration.match_to_application) runs this against every open
    application for the org and picks the highest-scoring one, only
    accepting it if score >= MATCH_THRESHOLD.
    """
    combined_text = f"{subject or ''} {body_snippet or ''}"
    sender_domain = _extract_sender_domain(sender_email)
    signals = {}
    score = 0.0

    # Domain signal — verified takes priority over guessed, never both
    if sender_domain and verified_domain and sender_domain == verified_domain.lower():
        score += WEIGHT_VERIFIED_DOMAIN
        signals["verified_domain_match"] = WEIGHT_VERIFIED_DOMAIN
    elif sender_domain:
        guessed = _guess_domain_from_company(job.get("company_name", ""))
        if guessed and sender_domain == guessed:
            score += WEIGHT_GUESSED_DOMAIN
            signals["guessed_domain_match"] = WEIGHT_GUESSED_DOMAIN

    # Company name in email text
    if _contains_word(combined_text, job.get("company_name", "")):
        score += WEIGHT_COMPANY_NAME
        signals["company_name_match"] = WEIGHT_COMPANY_NAME

    # Job title in email text
    if _contains_word(combined_text, job.get("job_title", "")):
        score += WEIGHT_JOB_TITLE
        signals["job_title_match"] = WEIGHT_JOB_TITLE

    # Recipient sanity check
    if recipient_email and onboarding_email and recipient_email.lower() == onboarding_email.lower():
        score += WEIGHT_RECIPIENT_EMAIL
        signals["recipient_email_match"] = WEIGHT_RECIPIENT_EMAIL

    # Recency tie-breaker
    if _is_recent(application.get("applied_at"), application.get("created_at", "")):
        score += WEIGHT_RECENCY
        signals["recent_application"] = WEIGHT_RECENCY

    return MatchResult(
        application_id=application["id"],
        score=score,
        signals=signals,
        is_confident=score >= MATCH_THRESHOLD,
    )


def find_best_match(
    sender_email: str,
    subject: str,
    body_snippet: str,
    recipient_email: str,
    onboarding_email: str,
    candidates: list[tuple[dict, dict, Optional[str]]],
) -> Optional[MatchResult]:
    """
    candidates: list of (application, job, verified_domain) tuples — one
    per open application to check. Returns the highest-scoring
    MatchResult, or None if no candidates were given. Caller must check
    .is_confident before acting on the result — a non-confident top match
    is still returned (useful for debugging/logging) but must not trigger
    an automatic status update.
    """
    if not candidates:
        return None

    results = [
        score_application_match(
            sender_email, subject, body_snippet, recipient_email, onboarding_email,
            application, job, verified_domain,
        )
        for application, job, verified_domain in candidates
    ]
    return max(results, key=lambda r: r.score)
