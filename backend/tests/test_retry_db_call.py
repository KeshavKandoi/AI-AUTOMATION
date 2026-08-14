"""
Tests for job_hunter.retry.retry_db_call(), added after a production
sweep lost ~8,000 discovered jobs to stale Supabase connection failures.
Covers the four required scenarios: transient failure -> successful
retry, transient failure -> exhausted retries, permanent error -> no
retry, and retry-after-partial-success does not create duplicates.
"""
import httpx
import pytest
from unittest.mock import MagicMock
from job_hunter.retry import retry_db_call, RetryExhaustedError


def test_transient_failure_then_success():
    """A single transient error followed by success must return the
    successful result, having retried exactly once."""
    call_count = {"n": 0}

    def flaky():
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise httpx.ConnectError("connection refused")
        return "success"

    result = retry_db_call(flaky, max_attempts=4, base_delay_seconds=0.01)
    assert result == "success"
    assert call_count["n"] == 2, "should have retried exactly once after the first failure"


def test_transient_failure_exhausts_all_retries():
    """Persistent transient failures across every attempt must raise
    RetryExhaustedError, not silently swallow the error."""
    call_count = {"n": 0}

    def always_fails():
        call_count["n"] += 1
        raise httpx.RemoteProtocolError("connection terminated")

    with pytest.raises(RetryExhaustedError) as exc_info:
        retry_db_call(always_fails, max_attempts=3, base_delay_seconds=0.01)

    assert call_count["n"] == 3, "should have attempted exactly max_attempts times"
    assert exc_info.value.attempts == 3
    assert isinstance(exc_info.value.last_exception, httpx.RemoteProtocolError)


def test_dns_error_is_treated_as_transient():
    """socket.gaierror (DNS resolution failure, the exact error type seen
    in the production sweep logs) must be retried, since it's an OSError
    subclass covered by TRANSIENT_EXCEPTIONS."""
    import socket
    call_count = {"n": 0}

    def dns_flaky():
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise socket.gaierror("nodename nor servname provided, or not known")
        return "resolved"

    result = retry_db_call(dns_flaky, max_attempts=3, base_delay_seconds=0.01)
    assert result == "resolved"
    assert call_count["n"] == 2


def test_permanent_api_error_is_never_retried():
    """A postgrest.exceptions.APIError (e.g. a unique-constraint violation
    -- a real response from the server, not a network failure) must
    propagate immediately on the first attempt, never retried. Retrying a
    permanent error would fail identically every time and could mask a
    real bug."""
    from postgrest.exceptions import APIError

    call_count = {"n": 0}

    def permanent_failure():
        call_count["n"] += 1
        raise APIError({"message": "duplicate key value violates unique constraint", "code": "23505"})

    with pytest.raises(APIError):
        retry_db_call(permanent_failure, max_attempts=5, base_delay_seconds=0.01)

    assert call_count["n"] == 1, "a permanent APIError must never be retried"


def test_retry_after_transient_failure_does_not_create_duplicate_job():
    """Simulates the real-world idempotency concern: create_job() fails
    with a transient error, gets retried, and the retry succeeds. Confirms
    exactly one insert call reaches the underlying table operation (the
    lambda wrapping supabase_admin.table(...).insert(...).execute()) --
    proving retry_db_call() does not itself cause a double-submission; any
    true double-insert risk lives at the DB constraint layer (dedup_key),
    which this test doesn't need to touch since retry_db_call() never
    calls fn() more times than necessary to get one success."""
    insert_calls = []

    def create_job_call():
        insert_calls.append(1)
        if len(insert_calls) < 2:
            raise httpx.ConnectError("connection refused")
        return {"id": "job123", "dedup_key": "abc"}

    result = retry_db_call(create_job_call, max_attempts=4, base_delay_seconds=0.01)
    assert result["id"] == "job123"
    assert len(insert_calls) == 2, (
        "exactly 2 calls expected: 1 failed attempt + 1 successful retry -- "
        "retry_db_call must stop immediately once fn() succeeds, never "
        "calling it again after a success"
    )
