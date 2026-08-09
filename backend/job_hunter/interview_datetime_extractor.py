"""
Interview datetime extraction: structured sources first (text/calendar
MIME parts, .ics attachments), LLM as a last-resort fallback only when
no structured source is present.

Design principle: structured extraction is authoritative (confidence is
always implicitly "high" — it's not inference, it's literally what the
calendar system reports) and must always be tried first. The LLM path is
only reached when extract_from_structured_sources() returns None, and
even then, a low-confidence or schema-invalid LLM result must result in
NO calendar event being created — the caller is responsible for treating
None as "skip calendar sync, but still record the Gmail event and update
application status."
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from icalendar import Calendar
from config import logger, gemini_client

LLM_CONFIDENCE_THRESHOLD = 70


@dataclass
class ExtractedInterview:
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    timezone: Optional[str]
    meeting_link: Optional[str]
    interviewer: Optional[str]
    company: Optional[str]
    source: str              # "ics" | "llm"
    confidence: float        # 100 for ics (authoritative), 0-100 for llm
    explanation: Optional[str] = None


def _walk_mime_parts(payload: dict) -> list[dict]:
    """Flattens a Gmail message payload's MIME tree into a list of parts,
    reusing the same recursive-walk shape as _extract_attachments in
    gmail_integration.py (kept separate here rather than imported, since
    this module has no other dependency on gmail_integration and importing
    it would create a needless coupling — the traversal logic itself is
    intentionally identical, not reinvented differently)."""
    parts = []

    def walk(part: dict):
        parts.append(part)
        for sub in part.get("parts", []):
            walk(sub)

    walk(payload)
    return parts


def _decode_part_body(part: dict) -> bytes:
    import base64
    data = part.get("body", {}).get("data", "")
    if not data:
        return b""
    try:
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    except Exception:
        return b""


def _parse_ics_bytes(ics_bytes: bytes) -> Optional[ExtractedInterview]:
    try:
        cal = Calendar.from_ical(ics_bytes)
    except Exception as e:
        logger.warning(f"Failed to parse .ics content: {e}")
        return None

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        dtstart = component.get("dtstart")
        dtend = component.get("dtend")
        if not dtstart:
            continue

        start_dt = dtstart.dt if hasattr(dtstart, "dt") else None
        end_dt = dtend.dt if dtend and hasattr(dtend, "dt") else None
        if not isinstance(start_dt, datetime):
            continue  # all-day / date-only events aren't useful for interview scheduling

        tz_name = str(start_dt.tzinfo) if start_dt.tzinfo else None

        location = str(component.get("location", "")) or None
        meeting_link = None
        if location and re.match(r"^https?://", location):
            meeting_link = location
        else:
            description = str(component.get("description", ""))
            link_match = re.search(
                r"(https://[^\s]*(?:zoom\.us|meet\.google\.com|teams\.microsoft\.com)[^\s]*)",
                description, re.IGNORECASE,
            )
            if link_match:
                meeting_link = link_match.group(1).rstrip(".,)")

        organizer = component.get("organizer")
        interviewer = str(organizer).replace("mailto:", "") if organizer else None

        return ExtractedInterview(
            start_time=start_dt,
            end_time=end_dt if isinstance(end_dt, datetime) else None,
            timezone=tz_name,
            meeting_link=meeting_link,
            interviewer=interviewer,
            company=None,  # not reliably present in ICS; caller has this from the job record already
            source="ics",
            confidence=100.0,
        )

    return None


def extract_from_structured_sources(msg: dict) -> Optional[ExtractedInterview]:
    """Checks every MIME part of a Gmail message for text/calendar content
    (inline invites) or .ics attachment filenames. Returns the first
    successfully parsed VEVENT, or None if nothing structured is found."""
    payload = msg.get("payload", {})
    parts = _walk_mime_parts(payload)

    for part in parts:
        mime_type = part.get("mimeType", "")
        filename = part.get("filename", "")

        is_calendar_mime = mime_type == "text/calendar"
        is_ics_attachment = filename.lower().endswith(".ics")

        if not (is_calendar_mime or is_ics_attachment):
            continue

        # Inline text/calendar parts have body data directly on the part.
        # .ics attachments referenced by attachmentId require a separate
        # Gmail API fetch — not handled here since it needs an HTTP client;
        # see gmail_integration.py's caller for the attachment-fetch step.
        ics_bytes = _decode_part_body(part)
        if not ics_bytes:
            continue

        result = _parse_ics_bytes(ics_bytes)
        if result:
            return result

    return None


LLM_EXTRACTION_PROMPT = """You are extracting interview scheduling details from a recruitment email. Analyze the email below and return ONLY a valid JSON object (no markdown, no explanation outside the JSON) with this exact structure:

{{
  "date": "YYYY-MM-DD or null if not determinable",
  "start_time": "HH:MM in 24-hour format or null",
  "end_time": "HH:MM in 24-hour format or null (estimate 1 hour after start if not stated)",
  "timezone": "IANA timezone name (e.g. America/New_York) or null if not determinable",
  "meeting_link": "URL or null",
  "interviewer": "name or null",
  "company": "company name or null",
  "confidence": 0-100 integer representing how certain you are of the extracted date/time,
  "explanation": "one short sentence on how you derived the date/time, or why confidence is low"
}}

Rules:
- If the email does not contain a specific date AND time for an interview, set confidence to 0.
- If the timezone is not explicitly stated or clearly inferable, set timezone to null and lower your confidence.
- Relative dates ("next Tuesday", "tomorrow") should be resolved using the email's own date context if available, otherwise lower confidence.
- Do not guess a date/time that isn't reasonably supported by the email text.

Email subject: {subject}

Email body:
{body}
"""


def extract_via_llm(subject: str, body_text: str, email_received_at: Optional[str] = None) -> Optional[ExtractedInterview]:
    """LLM fallback — only called when extract_from_structured_sources()
    returns None. Requires the model to return strict, schema-validated
    JSON with its own confidence score; anything below
    LLM_CONFIDENCE_THRESHOLD or that fails validation returns None,
    meaning no calendar event will be created (caller still proceeds with
    status update + Gmail event logging)."""
    prompt = LLM_EXTRACTION_PROMPT.format(subject=subject or "", body=(body_text or "")[:3000])

    try:
        response = gemini_client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
        raw_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw_text)
    except Exception as e:
        logger.warning(f"LLM datetime extraction failed or returned invalid JSON: {e}")
        return None

    required_keys = {"date", "start_time", "end_time", "timezone", "meeting_link", "interviewer", "company", "confidence", "explanation"}
    if not required_keys.issubset(data.keys()):
        logger.warning(f"LLM datetime extraction response missing required keys: {data.keys()}")
        return None

    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)) or confidence < LLM_CONFIDENCE_THRESHOLD:
        logger.info(f"LLM datetime extraction confidence too low ({confidence}) — skipping calendar sync")
        return None

    if not data.get("date") or not data.get("start_time"):
        logger.info("LLM datetime extraction did not produce a usable date/time — skipping calendar sync")
        return None

    try:
        from zoneinfo import ZoneInfo
        tz_name = data.get("timezone")
        tz = ZoneInfo(tz_name) if tz_name else None

        start_dt = datetime.fromisoformat(f"{data['date']}T{data['start_time']}")
        if tz:
            start_dt = start_dt.replace(tzinfo=tz)

        end_dt = None
        if data.get("end_time"):
            end_dt = datetime.fromisoformat(f"{data['date']}T{data['end_time']}")
            if tz:
                end_dt = end_dt.replace(tzinfo=tz)
    except Exception as e:
        logger.warning(f"LLM datetime extraction produced unparseable date/time: {e}")
        return None

    return ExtractedInterview(
        start_time=start_dt,
        end_time=end_dt,
        timezone=data.get("timezone"),
        meeting_link=data.get("meeting_link"),
        interviewer=data.get("interviewer"),
        company=data.get("company"),
        source="llm",
        confidence=float(confidence),
        explanation=data.get("explanation"),
    )


def extract_interview_datetime(msg: dict, subject: str, body_text: str) -> Optional[ExtractedInterview]:
    """Single entry point: tries structured sources first, only falls
    back to the LLM if nothing structured was found. This is the only
    function callers (gmail_integration.py) should use."""
    structured = extract_from_structured_sources(msg)
    if structured:
        return structured

    return extract_via_llm(subject, body_text)
