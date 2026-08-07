"""
Provider/adapter interface for Job Hunter platforms.

Every platform (Greenhouse, Lever, Ashby, YC Jobs, LinkedIn, Indeed,
Wellfound, Internshala, X, Telegram, company career pages, ...) implements
BaseJobProvider and registers itself via @register_provider in
job_hunter/platforms/registry.py. Nothing in job_hunter/service.py,
routes.py, or scheduler_jobs.py ever imports a specific platform — they
only talk to the registry, so adding, removing, or fixing one platform
never requires touching core code or any other platform.

Design principles:
- search() returns a list of RawJob — a normalized shape independent of
  how the platform represents jobs, so ingest_discovered_job() in
  job_hunter/service.py never needs to know which platform a job came from.
- A provider that isn't configured (missing API key, no OAuth connection)
  raises NotConfiguredError from is_configured()/search() rather than
  silently returning []  — the registry surfaces this as a distinct status
  ("not_configured") instead of conflating it with "ran and found nothing".
- A provider that fails mid-run (network error, API error, selector
  changed) raises ProviderError — the registry catches this per-provider
  so one broken platform never stops the others from running.
- retry_with_backoff() and RateLimiter are shared utilities so every
  provider gets consistent, tunable retry/rate-limit behavior instead of
  each reinventing it.
"""
import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable, TypeVar

from config import logger

T = TypeVar("T")


class NotConfiguredError(Exception):
    """Raised when a provider is missing required credentials/config.
    Distinct from ProviderError so the registry can report
    status='not_configured' instead of status='error'."""
    pass


class ProviderError(Exception):
    """Raised when a configured provider fails during a run (network,
    API error, parsing/selector failure, etc.)."""
    pass


@dataclass
class RawJob:
    """Normalized job shape every provider must return, regardless of how
    the source platform represents a job. This is what gets passed to
    job_hunter.service.ingest_discovered_job()."""
    company_name: str
    job_title: str
    original_apply_url: str
    platform: str
    platform_url: str

    platform_job_id: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None            # Remote / Hybrid / Onsite
    employment_type: Optional[str] = None       # Internship / Full-time / Part-time / Contract / Freelance
    experience_required: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    required_skills: list[str] = field(default_factory=list)
    qualifications: Optional[str] = None
    benefits: Optional[str] = None
    company_info: Optional[str] = None
    posted_at: Optional[str] = None   # ISO 8601 string


class RateLimiter:
    """Simple per-provider rate limiter: ensures at least `min_interval_seconds`
    passes between calls. Providers call await limiter.wait() before each
    outbound request (API call or page navigation)."""

    def __init__(self, min_interval_seconds: float):
        self.min_interval_seconds = min_interval_seconds
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self):
        async with self._lock:
            elapsed = time.monotonic() - self._last_call
            remaining = self.min_interval_seconds - elapsed
            if remaining > 0:
                await asyncio.sleep(remaining)
            self._last_call = time.monotonic()


async def retry_with_backoff(
    fn: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Retries an async callable with exponential backoff. Re-raises the
    last exception if all attempts are exhausted, so the caller (registry)
    can catch it and mark the provider run as failed without crashing the
    overall sweep."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except retry_on as e:
            last_exc = e
            if attempt < max_attempts:
                delay = base_delay_seconds * (2 ** (attempt - 1))
                logger.warning(f"Retry {attempt}/{max_attempts} after error: {e} (waiting {delay}s)")
                await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]


class BaseJobProvider(ABC):
    """Base class every platform adapter implements."""

    #: unique platform identifier, e.g. "greenhouse", "linkedin", "indeed"
    platform: str = ""

    #: how the provider integrates: "api" or "playwright" — purely
    #: informational, shown in provider status for transparency
    method: str = "api"

    def is_configured(self, organization_id: str) -> bool:
        """Returns whether this provider has what it needs to run for this
        org (API key present, OAuth integration connected, etc). Default
        True — override for providers that need credentials."""
        return True

    @abstractmethod
    async def search(self, organization_id: str, preferences: dict) -> list[RawJob]:
        """
        Searches this platform using the org's saved Job Hunter preferences
        (desired_roles, skills, employment_types, work_modes,
        preferred_locations, experience_level, etc.) and returns a list of
        RawJob. Must raise NotConfiguredError if is_configured() would be
        False, and ProviderError on any failure during the run — never
        return partial/fake data silently.
        """
        raise NotImplementedError
