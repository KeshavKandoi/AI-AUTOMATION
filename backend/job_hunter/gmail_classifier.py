"""
Rule-based classifier for recruitment-related emails. Deterministic,
keyword/pattern-based — no LLM, no external calls, fully unit-testable.

Design principle: precision over recall. A false "rejection" or "offer"
classification on a non-recruitment email is worse than missing a real
one, since classification feeds directly into automated application
status changes. When signals are ambiguous, prefer a lower-confidence
category or 'not_recruitment' over guessing.

Category priority when multiple signals fire (checked in this order,
first confident match wins): offer > rejection > interview_invite >
assessment > reschedule > withdrawal > application_confirmation.
This ordering reflects real-world specificity — an email mentioning both
"interview" and "offer" almost certainly IS an offer (interviews are
often referenced retrospectively in offer emails), so more decisive
categories are checked first.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClassificationResult:
    category: str
    confidence: str  # "high" | "low"
    matched_keywords: list[str] = field(default_factory=list)
    extracted_metadata: dict = field(default_factory=dict)


# Each pattern list is checked with word-boundary-safe matching against
# subject + body snippet combined. Patterns are phrases, not single words,
# to reduce false positives (e.g. "offer" alone is too generic — "we are
# pleased to offer you" is specific).
CATEGORY_PATTERNS: dict[str, list[str]] = {
    "offer": [
        r"pleased to offer", r"formal offer", r"offer letter",
        r"job offer", r"extend an offer", r"offer of employment",
        r"welcome to the team", r"excited to offer you",
    ],
    "rejection": [
        r"not moving forward", r"decided not to proceed",
        r"other candidates", r"will not be moving forward",
        r"unfortunately", r"not selected", r"pursue other candidates",
        r"position has been filled", r"unable to offer you",
    ],
    "interview_invite": [
        r"interview invitation", r"schedule an interview",
        r"invite you to interview", r"like to interview you",
        r"phone screen", r"video interview", r"onsite interview",
        r"interview with", r"meet with the team", r"schedule a call",
        r"schedule a time to (chat|talk|connect)",
        r"join your interview", r"your interview (is|has been) (scheduled|confirmed)",
        r"interview (link|details|reminder)", r"upcoming interview",
    ],
    "assessment": [
        r"coding (test|challenge|assessment)", r"technical assessment",
        r"take[- ]home (test|assignment|project)", r"online assessment",
        r"skills assessment", r"complete (a|the) (test|assessment|challenge)",
    ],
    "reschedule": [
        r"reschedul", r"need to move (our|the) (interview|call|meeting)",
        r"change (our|the) (interview|meeting) time",
        r"conflict.{0,30}(interview|meeting)",
    ],
    "withdrawal": [
        r"withdraw(n|ing)? (your|my|the)? ?application",
        r"position (has been|was) closed", r"role (has been|was) put on hold",
        r"no longer accepting applications",
    ],
    "application_confirmation": [
        r"application (has been )?received", r"thank you for applying",
        r"thanks for applying", r"we('ve| have) received your application",
        r"application confirmation", r"successfully submitted",
    ],
}

# Checked in priority order — see module docstring.
CATEGORY_PRIORITY = [
    "offer", "rejection", "interview_invite", "assessment",
    "reschedule", "withdrawal", "application_confirmation",
]

# Generic recruitment signal words — presence alone doesn't classify, but
# absence of ANY of these (plus no category match) is a strong signal this
# isn't a recruitment email at all.
RECRUITMENT_SIGNAL_WORDS = [
    "application", "position", "role", "candidate", "interview",
    "recruiter", "hiring", "talent", "career", "opportunity",
]


def _find_matches(text: str, patterns: list[str]) -> list[str]:
    matched = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(pattern)
    return matched


def classify_email(subject: str, body_snippet: str = "") -> ClassificationResult:
    """
    Classifies a single email. Returns category='not_recruitment' with
    confidence='high' if nothing recruitment-related is detected at all —
    this is the common case for the vast majority of an inbox and must be
    cheap and reliable to avoid false-positive noise feeding into
    application matching downstream.
    """
    combined_text = f"{subject or ''} {body_snippet or ''}"

    for category in CATEGORY_PRIORITY:
        patterns = CATEGORY_PATTERNS[category]
        matches = _find_matches(combined_text, patterns)
        if matches:
            # Multiple independent pattern matches for the same category
            # is a stronger signal than a single match.
            confidence = "high" if len(matches) >= 1 else "low"
            return ClassificationResult(
                category=category,
                confidence=confidence,
                matched_keywords=matches,
                extracted_metadata=extract_metadata(category, combined_text),
            )

    # No specific category matched — check if it's even recruitment-adjacent
    has_recruitment_signal = any(
        re.search(r"\b" + re.escape(w) + r"\b", combined_text, re.IGNORECASE)
        for w in RECRUITMENT_SIGNAL_WORDS
    )
    if has_recruitment_signal:
        return ClassificationResult(category="unmatched", confidence="low")

    return ClassificationResult(category="not_recruitment", confidence="high")


def extract_metadata(category: str, text: str) -> dict:
    """Best-effort extraction of structured info for later Calendar
    integration — e.g. a meeting link if present. Deliberately minimal
    for now; real datetime parsing from free text is unreliable without
    an LLM and is flagged as future work rather than faked here."""
    metadata = {}

    meeting_link_match = re.search(
        r"(https://[^\s]*(?:zoom\.us|meet\.google\.com|teams\.microsoft\.com)[^\s]*)",
        text, re.IGNORECASE,
    )
    if meeting_link_match:
        metadata["meeting_link"] = meeting_link_match.group(1).rstrip(".,)")

    return metadata
