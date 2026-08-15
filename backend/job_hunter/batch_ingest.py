"""
Batch ingestion path for Job Hunter discovery sweeps. Added after
measuring that per-job sequential ingestion (job_hunter/service.py's
original ingest_discovered_job(), 3-6 Supabase round-trips per job) took
~2.94 hours for 22,865 jobs. A 200-row batch upsert benchmark measured
0.93s for 200 rows (4.6ms/row) vs. ~463ms/job sequentially -- see
scheduler_jobs.run_search_for_org() for how this is wired into the real
sweep.

Preserves every existing guarantee:
- (organization_id, dedup_key) uniqueness -- same DB constraint, just
  hit via upsert instead of select-then-insert/update.
- is_active reactivation -- every batch row explicitly sets
  is_active=True; empirically verified (see batch-size benchmark script)
  that Supabase upsert with default_to_null=False leaves ALL other
  omitted columns untouched on conflict, and explicitly-set columns are
  applied normally on both insert and update.
- work_mode/employment_type self-heal (never overwrite an existing
  non-NULL value with NULL/uncertain) -- computed per-row before the
  batch upsert using a single batched existing-rows lookup
  (get_existing_by_dedup_keys) instead of N individual lookups.
- first_discovered_at/last_seen_at insert-vs-update detection -- same
  first_discovered_at == last_seen_at comparison as the original
  per-job path, applied to each row in the upsert response.
- Retry-safety -- batch_upsert_jobs() is wrapped in retry_db_call();
  retrying a whole batch is idempotent since upsert re-applies the same
  values regardless of whether the prior attempt actually landed.
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from config import logger
from job_hunter import repository
from job_hunter.service import build_dedup_key, _content_changed, MODULE
from job_hunter.notifications_shim import notify_job_match  # see below
from audit_logs.service import log_event

# Configurable batch size -- validated via a real 200-row upsert
# benchmark (0.93s, no errors). Do not increase without re-benchmarking
# at the new size first, per the production-safety requirement this was
# built under.
BATCH_SIZE = 200

# Bounded concurrency for the genuinely per-job operations that can't be
# trivially batched (add_job_source has a different platform/url per
# job; notify/log_event only fire for new/changed jobs). Runs these sync
# repository calls in a thread pool via asyncio.to_thread, capped by this
# semaphore -- never an unbounded gather() over the whole raw_jobs list.
PER_JOB_CONCURRENCY = 15


def _build_upsert_row(organization_id: str, raw_job, dedup_key: str, existing: Optional[dict]) -> dict:
    row = {
        "organization_id": organization_id,
        "dedup_key": dedup_key,
        "company_name": raw_job.company_name,
        "job_title": raw_job.job_title,
        "location": raw_job.location,
        "employment_type": raw_job.employment_type,
        "experience_required": raw_job.experience_required,
        "salary_min": raw_job.salary_min,
        "salary_max": raw_job.salary_max,
        "salary_currency": raw_job.salary_currency,
        "description": raw_job.description,
        "responsibilities": raw_job.responsibilities,
        "required_skills": raw_job.required_skills or [],
        "qualifications": raw_job.qualifications,
        "benefits": raw_job.benefits,
        "company_info": raw_job.company_info,
        "original_apply_url": raw_job.original_apply_url,
        "posted_at": raw_job.posted_at,
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
        # Reactivation: every rediscovered job (whether it was already
        # active or had gone stale) is explicitly set active here --
        # empirically verified safe/correct (see module docstring).
        "is_active": True,
    }

    # work_mode self-heal: never overwrite an existing non-NULL value
    # with a new NULL/uncertain one -- mirrors the exact logic from the
    # original per-job ingest_discovered_job().
    if existing and existing.get("work_mode") and not raw_job.work_mode:
        row["work_mode"] = existing["work_mode"]
    else:
        row["work_mode"] = raw_job.work_mode

    if existing and existing.get("employment_type") and not raw_job.employment_type:
        row["employment_type"] = existing["employment_type"]

    return row


async def _add_source_and_notify(organization_id: str, job_row: dict, raw_job, is_new: bool, content_changed: bool, sem: asyncio.Semaphore):
    async with sem:
        try:
            await asyncio.to_thread(
                repository.add_job_source,
                {
                    "job_id": job_row["id"],
                    "platform": raw_job.platform,
                    "platform_job_id": raw_job.platform_job_id,
                    "platform_url": raw_job.platform_url,
                },
            )
        except Exception as e:
            logger.error(f"[job_hunter] batch: failed to add_job_source for job {job_row['id']} ({raw_job.platform}): {e}")

        if is_new or content_changed:
            try:
                await asyncio.to_thread(
                    notify_job_match,
                    organization_id, job_row, raw_job, is_new,
                )
            except Exception as e:
                logger.error(f"[job_hunter] batch: failed to notify/log for job {job_row['id']}: {e}")


async def ingest_discovered_jobs_batch(organization_id: str, raw_jobs: list) -> dict:
    """Batched replacement for the sequential
    `for raw_job in raw_jobs: service.ingest_discovered_job(...)` loop.
    Returns the same metrics shape scheduler_jobs.run_search_for_org()
    already expects: inserted, updated, permanent_failures,
    permanent_failure_details, jobs_new (alias for inserted)."""
    inserted = 0
    updated = 0
    permanent_failures = []
    sem = asyncio.Semaphore(PER_JOB_CONCURRENCY)

    for batch_start in range(0, len(raw_jobs), BATCH_SIZE):
        batch = raw_jobs[batch_start:batch_start + BATCH_SIZE]

        dedup_keys = [
            build_dedup_key(rj.company_name, rj.job_title, rj.location, rj.original_apply_url)
            for rj in batch
        ]

        try:
            existing_map = repository.get_existing_by_dedup_keys(organization_id, dedup_keys)
        except Exception as e:
            logger.error(f"[job_hunter] batch: failed to fetch existing rows for batch at offset {batch_start}: {e}")
            for rj in batch:
                permanent_failures.append({
                    "platform": rj.platform, "company": rj.company_name,
                    "title": rj.job_title, "error": f"existing_lookup_failed: {e}",
                })
            continue

        upsert_rows = []
        for rj, dk in zip(batch, dedup_keys):
            existing = existing_map.get(dk)
            upsert_rows.append(_build_upsert_row(organization_id, rj, dk, existing))

        try:
            upserted = repository.batch_upsert_jobs(upsert_rows)
        except Exception as e:
            logger.error(f"[job_hunter] batch: upsert failed for batch at offset {batch_start} ({len(batch)} jobs): {e}")
            for rj in batch:
                permanent_failures.append({
                    "platform": rj.platform, "company": rj.company_name,
                    "title": rj.job_title, "error": f"batch_upsert_failed: {e}",
                })
            continue

        # Map upserted rows back to their raw_job by dedup_key to run the
        # per-job source/notify step and determine insert vs update.
        # counted_keys tracks which dedup_keys have already been counted
        # toward inserted/updated this batch -- two RawJobs that resolve
        # to the SAME dedup_key (e.g. the same posting found via two
        # different search queries within one sweep) map to the SAME
        # upserted DB row and must only be counted ONCE, even though the
        # per-job source/notify step still runs for each RawJob (each one
        # may carry a distinct platform_url worth recording as a source).
        upserted_by_key = {row["dedup_key"]: row for row in upserted}
        counted_keys = set()
        followup_tasks = []
        for rj, dk in zip(batch, dedup_keys):
            job_row = upserted_by_key.get(dk)
            if not job_row:
                permanent_failures.append({
                    "platform": rj.platform, "company": rj.company_name,
                    "title": rj.job_title, "error": "upserted row not found in response",
                })
                continue

            is_new = job_row.get("first_discovered_at") == job_row.get("last_seen_at")
            existing = existing_map.get(dk)
            content_changed = _content_changed(existing, rj.description, rj.salary_min, rj.salary_max) if existing else False

            if dk not in counted_keys:
                counted_keys.add(dk)
                if is_new:
                    inserted += 1
                else:
                    updated += 1

            followup_tasks.append(
                _add_source_and_notify(organization_id, job_row, rj, is_new, content_changed, sem)
            )

        if followup_tasks:
            await asyncio.gather(*followup_tasks)

    return {
        "inserted": inserted,
        "updated": updated,
        "jobs_new": inserted,
        "permanent_failures": len(permanent_failures),
        "permanent_failure_details": permanent_failures,
    }
