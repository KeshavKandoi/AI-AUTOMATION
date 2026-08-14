"""
Synchronous retry-with-backoff for Supabase/PostgREST database calls made
during job ingestion. Added after a production sweep lost ~8,000
successfully-discovered jobs when the long-lived module-level
supabase_admin httpx connection pool (config.py) accumulated stale
connections over a multi-hour sweep, surfacing as httpx.RemoteProtocolError
(wrapping low-level h2 ConnectionTerminated) and socket.gaierror (DNS
resolution) exceptions -- confirmed via direct inspection of the httpx and
postgrest exception hierarchies, not assumed.

Deliberately does NOT recreate/refresh the supabase_admin client -- that
would require coordinating client swaps across every module holding a
reference to it and risks connection-pool thrashing under concurrent
sweeps. Retrying the individual failed call is sufficient here because
httpx automatically discards a dead pooled connection and opens a fresh
one on the next request through the same client.
"""
import time
from typing import Callable, TypeVar, Optional

import httpx
from config import logger

T = TypeVar("T")

# Transient failure types: dead pooled connections, DNS hiccups, timeouts.
# Verified via direct inspection (see diagnostic script) that these do NOT
# overlap with postgrest.exceptions.APIError, which represents a real
# response from the server (schema errors, constraint violations,
# validation failures) and must never be retried -- retrying an APIError
# would just fail identically every time and could mask a real bug.
TRANSIENT_EXCEPTIONS = (httpx.TransportError, OSError, TimeoutError)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts for a DB call have been exhausted.
    Wraps the last underlying exception so callers can inspect it."""
    def __init__(self, last_exception: Exception, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(
            f"DB call failed after {attempts} attempt(s): {last_exception}"
        )


def retry_db_call(
    fn: Callable[[], T],
    max_attempts: int = 4,
    base_delay_seconds: float = 0.5,
    operation_name: Optional[str] = None,
) -> T:
    """
    Calls fn() and retries with exponential backoff (base_delay * 2^attempt)
    only on TRANSIENT_EXCEPTIONS. Any other exception (notably
    postgrest.exceptions.APIError -- permanent server-side errors like
    schema/constraint violations) propagates immediately on the first
    attempt, unretried.

    Idempotency: this retries the exact same fn() call, which for every
    current caller (create_job, update_job, add_job_source,
    get_job_by_dedup_key) is a single Supabase table operation. If the
    original request actually succeeded server-side but the response was
    lost in transit (the failure mode this is designed for -- a dead
    connection surfaces as a client-side exception even when the request
    may have landed), a retried create_job() could theoretically insert a
    second row. This is deliberately safe in practice: job identity is
    keyed on job_hunter_jobs.dedup_key (existing unique constraint,
    unrelated to this change), and job_hunter_job_sources rows are
    deduplicated by (job_id, platform, platform_url) in
    add_job_source() itself before inserting -- both already existing
    mechanisms this change does not touch. A retried insert either lands
    once (normal case) or collides with the existing unique constraint
    (rare race case), which surfaces as a permanent APIError on the retry
    and is correctly NOT retried further.

    Raises RetryExhaustedError if all attempts fail with a transient error.
    """
    label = operation_name or getattr(fn, "__name__", "db_call")
    last_exception: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except TRANSIENT_EXCEPTIONS as e:
            last_exception = e
            if attempt < max_attempts:
                delay = base_delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    f"[retry_db_call] Transient failure on '{label}' "
                    f"(attempt {attempt}/{max_attempts}): {type(e).__name__}: {e} "
                    f"-- retrying in {delay:.1f}s"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"[retry_db_call] '{label}' failed after {max_attempts} "
                    f"attempts, giving up: {type(e).__name__}: {e}"
                )
        # Deliberately no except-all here -- permanent errors (e.g.
        # postgrest.exceptions.APIError) propagate on first occurrence,
        # unretried, per the module docstring above.

    raise RetryExhaustedError(last_exception, max_attempts)
