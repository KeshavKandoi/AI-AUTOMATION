"""Shared age policy for discovered job listings."""

from datetime import datetime, timedelta, timezone
from typing import Optional

JOB_HUNTER_RETENTION_DAYS = 5


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def job_is_within_retention(
    posted_at: Optional[str],
    first_discovered_at: Optional[str] = None,
    now: Optional[datetime] = None,
) -> bool:
    """Keep listings for five days from posting, falling back to discovery.

    A missing or malformed source date falls back to first discovery. If
    neither timestamp exists, keep the item rather than age it by guesswork.
    """
    age_start = _parse_timestamp(posted_at) or _parse_timestamp(first_discovered_at)
    if age_start is None:
        return True
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return age_start >= current.astimezone(timezone.utc) - timedelta(days=JOB_HUNTER_RETENTION_DAYS)
