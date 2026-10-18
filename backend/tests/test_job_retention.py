"""
Tests for five-day job listing expiration, source refresh retention,
reactivation rules, and active-only filtering in list_jobs().
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


def test_list_jobs_combines_role_job_type_work_mode_and_employment_type():
    from job_hunter import repository

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.ilike.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[], count=0)

    with patch("job_hunter.repository.supabase_admin") as sb:
        sb.table.return_value.select.return_value = mock_query
        repository.list_jobs(
            "org1", role="Backend Engineer", job_type="engineering",
            work_mode="Remote", employment_type="Full-time",
        )

    eq_calls = [call.args for call in mock_query.eq.call_args_list]
    assert ("organization_id", "org1") in eq_calls
    assert ("is_active", True) in eq_calls
    assert ("work_mode", "Remote") in eq_calls
    assert ("employment_type", "Full-time") in eq_calls
    mock_query.ilike.assert_called_once_with("job_title", "%Backend Engineer%")
    mock_query.filter.assert_called_once_with(
        "job_title", "imatch", repository.JOB_CATEGORY_PATTERNS["engineering"]
    )


def test_remove_saved_job_requires_organization_ownership():
    from fastapi import HTTPException
    from job_hunter import service

    with patch("job_hunter.service.repository.get_application", return_value=None), \
            patch("job_hunter.service.repository.delete_application") as delete:
        try:
            service.delete_saved_job("org-a", "another-orgs-application")
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            assert False, "Deletion must reject an application outside the organization"
        delete.assert_not_called()


def test_remove_saved_job_deletes_related_records_but_not_discovered_job():
    from job_hunter import repository

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=[])
    with patch("job_hunter.repository.list_attachments", return_value=[]), \
            patch("job_hunter.repository.supabase_admin") as sb:
        sb.table.return_value.delete.return_value = mock_query
        repository.delete_application("org-a", "app-1")

    deleted_tables = [call.args[0] for call in sb.table.call_args_list]
    assert deleted_tables == [
        "job_hunter_attachments", "job_hunter_notes", "job_hunter_reminders",
        "job_hunter_activity", "job_hunter_applications",
    ]
    assert ("organization_id", "org-a") in [call.args for call in mock_query.eq.call_args_list]


def test_purge_expired_jobs_deletes_expired_untracked_listing_and_sources():
    from job_hunter import repository

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.in_.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.execute.side_effect = [
        MagicMock(data=[{"id": "expired", "posted_at": "2026-01-01T00:00:00+00:00", "first_discovered_at": "2026-01-01T00:00:00+00:00"}]),
        MagicMock(data=[]),  # no application tracker references it
        MagicMock(data=[]),  # source rows deleted
        MagicMock(data=[{"id": "expired"}]),  # listing deleted
    ]

    with patch("job_hunter.repository.supabase_admin") as sb:
        sb.table.return_value.select.return_value = mock_query
        sb.table.return_value.delete.return_value = mock_query
        now = datetime(2026, 1, 7, tzinfo=timezone.utc)
        result = repository.purge_expired_jobs("org1", now=now)

    assert result == {"deleted": 1, "retained_for_applications": 0}
    assert sb.table.call_args_list[0].args == ("job_hunter_jobs",)
    assert sb.table.call_args_list[-1].args == ("job_hunter_jobs",)
    # Expiration is queried by posted_at/first_discovered_at and job IDs;
    # source rows are removed before the listing row.
    assert sb.table.call_args_list[-2].args == ("job_hunter_job_sources",)


def test_purge_expired_jobs_keeps_application_history_and_hides_listing():
    from job_hunter import repository

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.in_.return_value = mock_query
    mock_query.range.return_value = mock_query
    mock_query.execute.side_effect = [
        MagicMock(data=[{"id": "tracked", "posted_at": "2026-01-01T00:00:00+00:00", "first_discovered_at": None}]),
        MagicMock(data=[{"job_id": "tracked"}]),
        MagicMock(data=[]),
    ]

    with patch("job_hunter.repository.supabase_admin") as sb:
        sb.table.return_value.select.return_value = mock_query
        sb.table.return_value.update.return_value = mock_query
        result = repository.purge_expired_jobs("org1", now=datetime(2026, 1, 7, tzinfo=timezone.utc))

    assert result == {"deleted": 0, "retained_for_applications": 1}
    sb.table.return_value.update.assert_called_once_with({"is_active": False})
    sb.table.return_value.delete.assert_not_called()


def test_jobs_expire_after_five_days_by_posted_date_not_last_seen():
    from job_hunter.scheduler_jobs import JOB_HUNTER_STALE_AFTER_DAYS
    from job_hunter.retention import job_is_within_retention

    assert JOB_HUNTER_STALE_AFTER_DAYS == 5
    now = datetime(2026, 1, 7, tzinfo=timezone.utc)
    assert not job_is_within_retention("2026-01-01T00:00:00+00:00", "2026-01-06T00:00:00+00:00", now)
    assert job_is_within_retention("2026-01-03T00:00:00+00:00", "2026-01-03T00:00:00+00:00", now)
    assert job_is_within_retention(None, "2026-01-06T00:00:00+00:00", now)


def test_provider_health_marks_old_status_as_stale():
    from job_hunter import repository

    old_status = {
        "organization_id": "org1",
        "platform": "greenhouse",
        "status": "active",
        "last_error": None,
        "last_run_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
    }
    with patch("job_hunter.repository.get_provider_statuses", return_value=[old_status]):
        result = repository.get_provider_health_summary("org1")

    assert result[0]["is_stale"] is True
    assert result[0]["is_healthy"] is False


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
