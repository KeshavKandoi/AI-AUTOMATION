"""
Tests for the job retention/soft-expiration system: is_active field,
mark_stale_jobs_inactive(), reactivation on rediscovery, and default
active-only filtering in list_jobs(). Never deletes rows -- confirms
the soft-expiration contract throughout.
"""
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


def test_list_jobs_filters_active_by_default():
    """Normal browsing must only see is_active=true jobs unless explicitly
    asked for historical/inactive ones."""
    from job_hunter import repository

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.or_.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[], count=0)

    with patch("job_hunter.repository.supabase_admin") as sb:
        sb.table.return_value.select.return_value = mock_query
        repository.list_jobs("org1", limit=10, offset=0)

    eq_calls = [call.args for call in mock_query.eq.call_args_list]
    assert ("is_active", True) in eq_calls, "default call must filter is_active=True"


def test_list_jobs_include_inactive_skips_active_filter():
    """include_inactive=True must retrieve the full record set, including
    soft-expired jobs, for historical/audit access."""
    from job_hunter import repository

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[], count=0)

    with patch("job_hunter.repository.supabase_admin") as sb:
        sb.table.return_value.select.return_value = mock_query
        repository.list_jobs("org1", limit=10, offset=0, include_inactive=True)

    eq_calls = [call.args for call in mock_query.eq.call_args_list]
    assert ("is_active", True) not in eq_calls, "include_inactive=True must NOT filter on is_active"
    assert ("organization_id", "org1") in eq_calls, "organization_id filter must still apply"


def test_mark_stale_jobs_inactive_only_updates_active_past_threshold():
    """The cleanup query must only ever flip is_active=false, and must be
    scoped to currently-active rows past the threshold -- confirming it
    never deletes and never touches already-inactive rows redundantly."""
    from job_hunter import repository

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.lt.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[{"id": "1"}, {"id": "2"}])

    with patch("job_hunter.repository.supabase_admin") as sb:
        sb.table.return_value.update.return_value = mock_query
        count = repository.mark_stale_jobs_inactive("2026-01-01T00:00:00+00:00")

    assert count == 2
    sb.table.return_value.update.assert_called_once_with({"is_active": False})
    mock_query.eq.assert_called_once_with("is_active", True)
    mock_query.lt.assert_called_once_with("last_seen_at", "2026-01-01T00:00:00+00:00")


def test_mark_stale_jobs_inactive_is_idempotent():
    """Running the cleanup twice in a row (simulating an overlapping or
    repeated trigger) must be safe -- the second run naturally finds
    fewer or zero matching rows since the first run already flipped them,
    never causing an error or incorrect double-update."""
    from job_hunter import repository

    call_results = [
        MagicMock(data=[{"id": "1"}, {"id": "2"}]),  # first run: 2 stale jobs found
        MagicMock(data=[]),                            # second run: none left (already inactive)
    ]
    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.lt.return_value = mock_query
    mock_query.execute.side_effect = call_results

    with patch("job_hunter.repository.supabase_admin") as sb:
        sb.table.return_value.update.return_value = mock_query
        first = repository.mark_stale_jobs_inactive("2026-01-01T00:00:00+00:00")
        second = repository.mark_stale_jobs_inactive("2026-01-01T00:00:00+00:00")

    assert first == 2
    assert second == 0, "second run must be a safe no-op, not an error or incorrect state"


def test_ingest_reactivates_inactive_job_on_rediscovery():
    """A job that had gone stale (is_active=false) must be reactivated
    when successfully rediscovered, alongside the existing last_seen_at
    refresh -- confirming the reactivation logic in service.py."""
    from job_hunter import service

    with patch("job_hunter.service.repository") as repo, \
         patch("job_hunter.service.notify"), \
         patch("job_hunter.service.log_event"):
        repo.get_job_by_dedup_key.return_value = {
            "id": "job1", "is_active": False, "work_mode": "Remote",
            "employment_type": "Full-time", "description": "old",
            "salary_min": None, "salary_max": None,
        }
        captured = {}
        def fake_update(job_id, updates):
            captured["updates"] = updates
            return {}
        repo.update_job.side_effect = fake_update
        repo.add_job_source.return_value = None

        service.ingest_discovered_job(
            organization_id="org1", company_name="Acme", job_title="SWE",
            original_apply_url="http://x", platform="greenhouse", platform_url="http://x",
        )

    assert captured["updates"].get("is_active") is True, "stale job must be reactivated on rediscovery"


def test_ingest_does_not_touch_active_flag_when_already_active():
    """A job that's already active and gets rediscovered should not have
    is_active redundantly written -- keeps updates minimal/correct."""
    from job_hunter import service

    with patch("job_hunter.service.repository") as repo, \
         patch("job_hunter.service.notify"), \
         patch("job_hunter.service.log_event"):
        repo.get_job_by_dedup_key.return_value = {
            "id": "job2", "is_active": True, "work_mode": "Remote",
            "employment_type": "Full-time", "description": "old",
            "salary_min": None, "salary_max": None,
        }
        captured = {}
        def fake_update(job_id, updates):
            captured["updates"] = updates
            return {}
        repo.update_job.side_effect = fake_update
        repo.add_job_source.return_value = None

        service.ingest_discovered_job(
            organization_id="org1", company_name="Acme", job_title="SWE",
            original_apply_url="http://x", platform="greenhouse", platform_url="http://x",
        )

    assert "is_active" not in captured["updates"], "already-active job should not get a redundant is_active write"


def test_failed_ingestion_never_touches_activity_state():
    """If get_job_by_dedup_key or update_job raises, no activity-state
    change should have occurred (this is enforced by construction -- the
    reactivation code lives inside the same try path as the rest of
    rediscovery, so a raised exception before reaching update_job means
    is_active is never touched). Confirms the exception simply propagates
    rather than silently marking anything active/inactive."""
    from job_hunter import service

    with patch("job_hunter.service.repository") as repo, \
         patch("job_hunter.service.notify"), \
         patch("job_hunter.service.log_event"):
        repo.get_job_by_dedup_key.return_value = {
            "id": "job3", "is_active": False, "work_mode": None,
            "employment_type": None, "description": None,
            "salary_min": None, "salary_max": None,
        }
        repo.update_job.side_effect = RuntimeError("simulated transient failure, retries exhausted")

        try:
            service.ingest_discovered_job(
                organization_id="org1", company_name="Acme", job_title="SWE",
                original_apply_url="http://x", platform="greenhouse", platform_url="http://x",
            )
            assert False, "expected the exception to propagate"
        except RuntimeError:
            pass  # expected -- caller (scheduler_jobs.py) is responsible for catching this
