"""
Shared job-matching logic. Every provider (API-based or Playwright-based)
filters its raw results through matches_preferences() before returning
them, so matching behavior is consistent across platforms and only needs
to be tuned in one place.

Uses word-boundary regex matching rather than naive substring checks —
short skill tokens like "Go", "R", "C" would otherwise false-positive
match inside unrelated words ("Google", "storage", "going", "concrete").

Deliberately lenient on missing signals: when location or employment type
is missing/unparseable from the source, we don't filter the job out on
that basis — better to surface a possibly-irrelevant job than silently
drop a real match because a platform's data was incomplete. Role/skill
text matching is the one filter applied strictly, since it's the primary
relevance signal.
"""
import re
from typing import Optional

EMPLOYMENT_TYPE_MAP = {
    "fulltime": "Full-time",
    "parttime": "Part-time",
    "intern": "Internship",
    "internship": "Internship",
    "contract": "Contract",
    "contractor": "Contract",
    "temporary": "Contract",
    "freelance": "Freelance",
}


def normalize_employment_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = raw.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    return EMPLOYMENT_TYPE_MAP.get(key, raw)


def _contains_word(haystack: str, needle: str) -> bool:
    """Word-boundary substring match. For multi-word needles (e.g. "backend
    engineer"), requires the exact phrase with boundaries on both ends —
    still safe for short tokens like "Go" or "R" since \\b anchors to
    word edges, not just any substring."""
    if not needle:
        return False
    pattern = r"\b" + re.escape(needle) + r"\b"
    return re.search(pattern, haystack, re.IGNORECASE) is not None


def matches_preferences(
    preferences: dict,
    title: str,
    description: str = "",
    location: str = "",
    employment_type: str = "",
) -> bool:
    title_l = title or ""
    desc_l = description or ""
    location_l = (location or "").lower()
    emp_l = (employment_type or "").lower()

    desired_roles = preferences.get("desired_roles", [])
    skills = preferences.get("skills", [])
    preferred_locations = [l.lower() for l in preferences.get("preferred_locations", [])]
    work_modes = [w.lower() for w in preferences.get("work_modes", [])]
    employment_types = [e.lower() for e in preferences.get("employment_types", [])]

    # Role/skill match is the primary relevance filter. Title-only —
    # description text is unreliable for this: many ATS postings include
    # generic company/tech-stack boilerplate ("We use Python, Go...") in
    # every job's description regardless of role, so matching skills
    # against description produces false positives (e.g. an Account
    # Executive posting matching because the company-wide blurb mentions
    # "Go"). A future pass could re-introduce description-level matching
    # with an LLM judging actual relevance rather than substring presence.
    if desired_roles or skills:
        role_match = any(_contains_word(title_l, role) for role in desired_roles)
        skill_in_title = any(_contains_word(title_l, skill) for skill in skills)
        if not (role_match or skill_in_title):
            return False

    # Location / work mode match — only filters when we actually have a location
    if location_l and (preferred_locations or work_modes):
        loc_match = any(pl in location_l for pl in preferred_locations)
        if "remote" in work_modes and "remote" in location_l:
            loc_match = True
        if not loc_match:
            return False

    # Employment type — only filters when both sides are known
    if employment_types and emp_l:
        if not any(et in emp_l for et in employment_types):
            return False

    return True
