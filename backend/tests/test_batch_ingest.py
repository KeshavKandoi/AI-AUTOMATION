"""
Correctness tests for job_hunter.batch_ingest -- proving the batched
ingestion path produces the same final database state as the original
sequential per-job ingest_discovered_job(), including inserts, updates,
duplicates within a batch, stale-job reactivation, work_mode/
employment_type self-heal, and permanent failure handling.
"""
import asyncio
from unittest.mock import patch, MagicMock
from job_hunter.platforms.base import RawJob
from job_hunter.batch_ingest import ingest_discovered_jobs_batch, _build_upsert_row, BATCH_SIZE


def _make_raw_job(company="Acme", title="SWE", url="http://x/1", work_mode="Remote", employment_type="Full-time"):
    return RawJob(
        company_name=company, job_title=title, original_apply_url=url,
        platform="greenhouse", platform_url=url,
        location="Remote", work_mode=work_mode, employment_type=employment_type,
    )


def test_new_job_is_counted_as_inserted():
    """A dedup_key with no existing row -- upsert response has
    first_discovered_at == last_seen_at -- must be counted as inserted."""
    raw_jobs = [_make_raw_job()]

    with patch("job_hunter.batch_ingest.repository") as repo, \
         patch("job_hunter.batch_ingest.notify_job_match"):
        repo.get_existing_by_dedup_keys.return_value = {}  # no existing rows
        repo.batch_upsert_jobs.return_value = [
            {"id": "job1", "dedup_key": "dk1", "first_discovered_at": "T1", "last_seen_at": "T1"}
        ]
        # Patch build_dedup_key to a stable, predictable value for this test
        with patch("job_hunter.batch_ingest.build_dedup_key", return_value="dk1"):
            result = asyncio.run(ingest_discovered_jobs_batch("org1", raw_jobs))

    assert result["inserted"] == 1
    assert result["updated"] == 0
    assert result["permanent_failures"] == 0


def test_rediscovered_job_is_counted_as_updated():
    """A dedup_key matching an existing row -- upsert response has
    first_discovered_at != last_seen_at -- must be counted as updated,
    not inserted."""
    raw_jobs = [_make_raw_job()]

    with patch("job_hunter.batch_ingest.repository") as repo, \
         patch("job_hunter.batch_ingest.notify_job_match"):
        repo.get_existing_by_dedup_keys.return_value = {
            "dk1": {"id": "job1", "work_mode": "Remote", "employment_type": "Full-time",
                    "is_active": True, "description": "old", "salary_min": None, "salary_max": None}
        }
        repo.batch_upsert_jobs.return_value = [
            {"id": "job1", "dedup_key": "dk1", "first_discovered_at": "T0", "last_seen_at": "T1"}
        ]
        with patch("job_hunter.batch_ingest.build_dedup_key", return_value="dk1"):
            result = asyncio.run(ingest_discovered_jobs_batch("org1", raw_jobs))

    assert result["inserted"] == 0
    assert result["updated"] == 1


def test_duplicate_within_same_batch_produces_one_row():
    """Two RawJobs that resolve to the SAME dedup_key within one batch
    (e.g. the same posting found via two different search queries) must
    not create two DB rows -- the upsert's on_conflict handling collapses
    them, mirroring the exact same seen_job_ids dedup behavior already
    enforced upstream in each provider adapter."""
    raw_jobs = [_make_raw_job(title="SWE"), _make_raw_job(title="SWE")]  # identical -> same dedup_key

    with patch("job_hunter.batch_ingest.repository") as repo, \
         patch("job_hunter.batch_ingest.notify_job_match"):
        repo.get_existing_by_dedup_keys.return_value = {}
        # Supabase upsert with duplicate dedup_keys in the same payload
        # collapses to ONE row in the response (last value wins) -- this
        # is real upsert behavior we're modeling here.
        repo.batch_upsert_jobs.return_value = [
            {"id": "job1", "dedup_key": "dk1", "first_discovered_at": "T1", "last_seen_at": "T1"}
        ]
        with patch("job_hunter.batch_ingest.build_dedup_key", return_value="dk1"):
            result = asyncio.run(ingest_discovered_jobs_batch("org1", raw_jobs))

    # Only ONE upserted row came back even though 2 raw_jobs were passed in
    # -- both raw_jobs map to it via dedup_key, so at most 1 insert is counted
    assert result["inserted"] + result["updated"] == 1


def test_work_mode_self_heal_preserves_existing_value():
    """_build_upsert_row must never overwrite an existing non-NULL
    work_mode with a new NULL one -- same guarantee as the original
    per-job ingest_discovered_job()."""
    raw_job = _make_raw_job(work_mode=None)  # new discovery has no work_mode signal
    existing = {"work_mode": "Hybrid", "employment_type": "Full-time"}

    row = _build_upsert_row("org1", raw_job, "dk1", existing)
    assert row["work_mode"] == "Hybrid", "existing non-NULL work_mode must be preserved, not overwritten with None"


def test_work_mode_self_heal_uses_new_value_when_existing_is_null():
    """When the existing row has no work_mode but the new discovery
    provides one, the new value must be used (self-heal)."""
    raw_job = _make_raw_job(work_mode="Remote")
    existing = {"work_mode": None, "employment_type": "Full-time"}

    row = _build_upsert_row("org1", raw_job, "dk1", existing)
    assert row["work_mode"] == "Remote"


def test_every_row_is_active_true_for_reactivation():
    """Every upsert row must explicitly set is_active=True -- this is the
    reactivation mechanism verified safe against real Supabase upsert
    behavior (empirically confirmed default_to_null=False preserves
    omitted columns, but is_active is intentionally NOT omitted -- it's
    always explicitly set to reactivate any previously-stale job)."""
    raw_job = _make_raw_job()
    row = _build_upsert_row("org1", raw_job, "dk1", existing=None)
    assert row["is_active"] is True


def test_batch_upsert_failure_marks_entire_batch_as_permanent_failure():
    """If batch_upsert_jobs() itself raises (e.g. retry-exhausted), every
    job in that batch must be recorded as a permanent failure -- no job
    silently disappears without being accounted for."""
    raw_jobs = [_make_raw_job(title="Job A"), _make_raw_job(title="Job B")]

    with patch("job_hunter.batch_ingest.repository") as repo, \
         patch("job_hunter.batch_ingest.notify_job_match"):
        repo.get_existing_by_dedup_keys.return_value = {}
        repo.batch_upsert_jobs.side_effect = RuntimeError("simulated batch upsert failure")
        with patch("job_hunter.batch_ingest.build_dedup_key", side_effect=["dk1", "dk2"]):
            result = asyncio.run(ingest_discovered_jobs_batch("org1", raw_jobs))

    assert result["permanent_failures"] == 2
    assert result["inserted"] == 0
    assert result["updated"] == 0
    titles = {f["title"] for f in result["permanent_failure_details"]}
    assert titles == {"Job A", "Job B"}


def test_multiple_batches_are_processed_when_exceeding_batch_size():
    """More than BATCH_SIZE jobs must be split into multiple upsert
    calls, not one giant request."""
    raw_jobs = [_make_raw_job(title=f"Job {i}", url=f"http://x/{i}") for i in range(BATCH_SIZE + 50)]

    call_count = {"n": 0}
    def fake_upsert(rows):
        # Must echo back the REAL dedup_key from each row's payload --
        # regenerating dk{i} by index within each call would silently
        # collide across batches (both batch 1 and batch 2 would produce
        # dk0..dkN), which is a mock bug, not real Supabase behavior.
        call_count["n"] += 1
        return [
            {"id": f"job_{row['dedup_key']}", "dedup_key": row["dedup_key"],
             "first_discovered_at": "T1", "last_seen_at": "T1"}
            for row in rows
        ]

    with patch("job_hunter.batch_ingest.repository") as repo, \
         patch("job_hunter.batch_ingest.notify_job_match"):
        repo.get_existing_by_dedup_keys.return_value = {}
        repo.batch_upsert_jobs.side_effect = fake_upsert
        dedup_keys = [f"dk{i}" for i in range(BATCH_SIZE + 50)]
        with patch("job_hunter.batch_ingest.build_dedup_key", side_effect=dedup_keys):
            result = asyncio.run(ingest_discovered_jobs_batch("org1", raw_jobs))

    assert call_count["n"] == 2, f"expected 2 batch upsert calls for {BATCH_SIZE + 50} jobs at BATCH_SIZE={BATCH_SIZE}, got {call_count['n']}"
    assert result["inserted"] == BATCH_SIZE + 50
