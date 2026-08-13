"""
Shared job-matching logic. Every provider (API-based or Playwright-based)
filters its raw results through matches_preferences() before returning
them, so matching behavior is consistent across platforms and only needs
to be tuned in one place.

Uses word-boundary regex matching rather than naive substring checks —
short skill tokens like "Go", "R", "C" would otherwise false-positive
match inside unrelated words ("Google", "storage", "going", "concrete").

Deliberately lenient on missing/ambiguous signals across the board:
location, employment type, experience, and salary are only used to filter
a job OUT when there's a clear, unambiguous mismatch — never on missing or
unparseable data. Role/skill text matching is the one filter applied
strictly, since it's the primary relevance signal. This mirrors real bugs
found and fixed during development (YC Jobs, career_pages): being strict
on ambiguous signals produces false negatives that silently hide real
matches, which is worse than occasionally surfacing an irrelevant one.

Experience and salary filtering are NEW (previously these onboarding
fields were collected but never used) — see matches_preferences() docstring
for the exact filtering rules and their rationale.
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

# Experience-level personas map to an approximate years-of-experience
# ceiling used only as a fallback when the user didn't give an explicit
# years_of_experience number. Deliberately generous (not the exact
# boundary) since this is a fallback signal, not the primary one.
EXPERIENCE_LEVEL_YEARS_CEILING = {
    "student": 0,
    "fresher": 1,
}


def normalize_employment_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = raw.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    return EMPLOYMENT_TYPE_MAP.get(key, raw)


WORK_MODE_MAP = {
    "remote": "Remote",
    "remoteonly": "Remote",
    "fullyremote": "Remote",
    "workfromhome": "Remote",
    "wfh": "Remote",
    "hybrid": "Hybrid",
    "onsite": "On-site",
    "onsiteonly": "On-site",
    "inoffice": "On-site",
    "office": "On-site",
    "inperson": "On-site",
}


def normalize_work_mode(raw: Optional[str]) -> Optional[str]:
    """Maps a provider's raw work-mode text to exactly one of the three
    canonical database values: "Remote", "Hybrid", "On-site". Returns None
    for anything ambiguous or unrecognized -- callers must never guess a
    work mode from a bare location/city/country name. This is the single
    shared normalizer every provider adapter routes explicit work-mode
    signals through, so the database never accumulates variant spellings
    (remote / REMOTE / WFH / Onsite / In office / ...)."""
    if not raw:
        return None
    key = raw.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    return WORK_MODE_MAP.get(key)


def _contains_word(haystack: str, needle: str) -> bool:
    """Word-boundary substring match. For multi-word needles (e.g. "backend
    engineer"), requires the exact phrase with boundaries on both ends —
    still safe for short tokens like "Go" or "R" since \\b anchors to
    word edges, not just any substring."""
    if not needle:
        return False
    pattern = r"\b" + re.escape(needle) + r"\b"
    return re.search(pattern, haystack, re.IGNORECASE) is not None


def parse_experience_years(text: Optional[str]) -> Optional[float]:
    """Extracts a minimum years-of-experience number from free text like
    '5 years of exp', '1 year(s)', 'No experience required', '0 - 1 year'.
    Returns None if unparseable — callers must treat None as "unknown",
    not "zero". Explicit "no experience" phrasing returns 0.0.
    """
    if not text:
        return None
    text_l = text.lower()

    if "no experience" in text_l or "fresher" in text_l:
        return 0.0

    match = re.search(r"(\d+(?:\.\d+)?)\s*[-–]?\s*(?:to)?\s*\d*\s*year", text_l)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None

    return None


def _experience_mismatch(preferences: dict, experience_text: Optional[str]) -> bool:
    """Returns True only when there's a CLEAR mismatch — the job's stated
    minimum experience meaningfully exceeds what the user has. Never
    returns True on ambiguous/unparseable data (lenient by default)."""
    job_years = parse_experience_years(experience_text)
    if job_years is None:
        return False  # unknown — never filter on missing data

    user_years = preferences.get("years_of_experience")
    if user_years is None:
        exp_level = preferences.get("experience_level")
        user_years = EXPERIENCE_LEVEL_YEARS_CEILING.get(exp_level) if exp_level else None
    if user_years is None:
        return False  # user gave no signal — never filter

    # Generous tolerance: only reject when the job asks for meaningfully
    # more experience than the user has (2+ year gap), not a borderline
    # 1-year difference a fresher might reasonably still apply to.
    return job_years > user_years + 2


def _salary_mismatch(preferences: dict, salary_min: Optional[float], salary_currency: Optional[str]) -> bool:
    """Returns True only when the job's salary is clearly, unambiguously
    below the user's stated minimum expectation — and only when both
    sides share a known, matching currency (comparing raw numbers across
    currencies would silently produce nonsense, e.g. INR vs USD)."""
    expected_min = preferences.get("expected_salary_min")
    if expected_min is None or salary_min is None:
        return False  # missing signal on either side — never filter

    expected_currency = preferences.get("salary_currency")
    if not expected_currency or not salary_currency:
        return False  # currency unknown on either side — can't safely compare
    if expected_currency.upper() != salary_currency.upper():
        return False  # different currencies — can't safely compare numbers directly

    # Generous tolerance: only reject when the job's floor is well below
    # (< 70%) the user's stated minimum, not a marginal shortfall.
    return salary_min < (expected_min * 0.7)


def matches_preferences(
    preferences: dict,
    title: str,
    description: str = "",
    location: str = "",
    employment_type: str = "",
    experience_text: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_currency: Optional[str] = None,
    work_mode: Optional[str] = None,
) -> bool:
    """
    experience_text / salary_min / salary_currency / work_mode are optional
    and backward compatible — existing call sites that don't pass them are
    unaffected (those filters simply never trigger, same as before this
    change). Providers that already extract this data at scrape time
    should pass it through for the new filtering to take effect.

    work_mode, when provided, must already be one of the canonical values
    ("Remote", "Hybrid", "On-site") -- callers should route raw provider
    text through normalize_work_mode() before passing it here. When not
    provided, work-mode filtering falls back to the original substring
    check against the raw location text (fully backward compatible).
    """
    title_l = title or ""
    location_l = (location or "").lower()
    emp_l = (employment_type or "").lower()

    desired_roles = preferences.get("desired_roles", [])
    skills = preferences.get("skills", [])
    preferred_locations = [l.lower() for l in preferences.get("preferred_locations", [])]
    work_modes = [w.lower() for w in preferences.get("work_modes", [])]
    employment_types = [e.lower() for e in preferences.get("employment_types", [])]

    # Role/skill match is the primary relevance filter. Title-only —
    # description text is unreliable for this (see module docstring).
    if desired_roles or skills:
        role_match = any(_contains_word(title_l, role) for role in desired_roles)
        skill_in_title = any(_contains_word(title_l, skill) for skill in skills)
        if not (role_match or skill_in_title):
            return False

    # Location / work mode match — only filters when we have something to check
    work_mode_l = (normalize_work_mode(work_mode) or "").lower()
    if (location_l or work_mode_l) and (preferred_locations or work_modes):
        loc_match = any(pl in location_l for pl in preferred_locations) if location_l else False
        if work_mode_l:
            # Provider gave us an explicit, already-normalized work mode --
            # trust it directly instead of re-deriving "remote" from raw
            # location text (which some providers strip the word out of).
            if work_mode_l in work_modes:
                loc_match = True
        elif "remote" in work_modes and "remote" in location_l:
            loc_match = True
        if not loc_match:
            return False

    # Employment type — only filters when both sides are known
    if employment_types and emp_l:
        if not any(et in emp_l for et in employment_types):
            return False

    # Experience — only filters on a clear, unambiguous mismatch
    if _experience_mismatch(preferences, experience_text):
        return False

    # Salary — only filters on a clear, unambiguous, same-currency mismatch
    if _salary_mismatch(preferences, salary_min, salary_currency):
        return False

    return True
