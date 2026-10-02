"""
Regression tests: routes patched to use get_current_org_id must actually be
able to call their service-layer functions without a TypeError, and must
ignore any client-forged organization_id in the request body. These tests
exist because signature mismatches between routes and services import
cleanly but fail at request time -- import success is not proof of
correctness.
"""
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


def _override_org(app, org_id="org-1"):
    from auth.dependencies import get_current_org_id
    app.dependency_overrides[get_current_org_id] = lambda: org_id


def _clear(app):
    app.dependency_overrides.clear()


def test_create_email_job_uses_trusted_org_id_not_body():
    from main import app
    _override_org(app, org_id="org-real")
    try:
        with patch("email_scheduler.routes.service.create_scheduled_job", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"id": "job-1", "organization_id": "org-real"}
            client = TestClient(app)
            res = client.post("/email-jobs", json={
                "organization_id": "org-attacker-forged",
                "to_email": "a@b.com",
                "subject": "hi",
                "body": "hi",
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
            })
            assert res.status_code == 200
            mock_create.assert_called_once()
            assert mock_create.call_args.kwargs.get("organization_id") == "org-real"
    finally:
        _clear(app)


def test_create_commit_job_uses_trusted_org_id_not_body():
    from main import app
    _override_org(app, org_id="org-real")
    try:
        with patch("commit_scheduler.routes.service.create_scheduled_job", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"id": "job-1", "organization_id": "org-real"}
            client = TestClient(app)
            res = client.post("/commit-jobs", json={
                "organization_id": "org-attacker-forged",
                "repo_full_name": "x/y",
                "branch": "main",
                "provider": "github",
                "mode": "guard",
                "commit_message": "auto",
                "start_date": "2026-09-01",
                "end_date": "2026-09-30",
            })
            assert res.status_code == 200
            mock_create.assert_called_once()
            assert mock_create.call_args.kwargs.get("organization_id") == "org-real"
    finally:
        _clear(app)


def test_upsert_lunch_block_settings_uses_trusted_org_id_not_body():
    from main import app
    _override_org(app, org_id="org-real")
    try:
        with patch("calendar_automation.routes.service.upsert_settings") as mock_upsert:
            mock_upsert.return_value = {"organization_id": "org-real"}
            client = TestClient(app)
            res = client.post("/lunch-block/settings", json={
                "organization_id": "org-attacker-forged",
                "enabled": True,
                "start_time": "12:00",
                "end_time": "13:00",
                "title": "Lunch",
                "weekdays_only": True,
            })
            assert res.status_code == 200
            mock_upsert.assert_called_once()
            assert mock_upsert.call_args.kwargs.get("organization_id") == "org-real"
    finally:
        _clear(app)


def test_orchestrator_run_endpoint_is_not_exposed():
    from main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/orchestrator/run" not in paths


def test_scheduler_control_routes_removed_and_status_requires_auth():
    from fastapi.testclient import TestClient
    from main import app
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/scheduler/pause" not in paths and "/scheduler/resume" not in paths
    assert TestClient(app).get("/scheduler/status").status_code == 401


def test_by_id_ownership_helpers_require_organization_id():
    import inspect
    from commit_scheduler import service as cs
    from email_scheduler import service as es
    from memory import service as ms
    for fn in (cs.get_job_or_404, es.get_job_or_404, ms.get_memory_or_404):
        assert inspect.signature(fn).parameters["organization_id"].default is inspect.Parameter.empty


def test_commit_job_file_delete_requires_file_to_belong_to_job(monkeypatch):
    import pytest
    from fastapi import HTTPException
    from commit_scheduler import routes
    deleted = []
    monkeypatch.setattr(routes.service, "get_job_or_404", lambda job_id, org_id: {"id": job_id})
    monkeypatch.setattr(routes.repository, "get_files_for_job", lambda job_id: [{"id": "f1"}])
    monkeypatch.setattr(routes.repository, "delete_job_file", lambda file_id: deleted.append(file_id))
    with pytest.raises(HTTPException) as exc:
        routes.delete_file("job1", "someone-elses-file", org_id="org1")
    assert exc.value.status_code == 404 and deleted == []
    routes.delete_file("job1", "f1", org_id="org1")
    assert deleted == ["f1"]


def test_email_job_schema_limits_and_single_line_subject():
    import pytest
    from datetime import date
    from pydantic import ValidationError
    from email_scheduler.schemas import EmailJobCreate
    base = dict(organization_id="o", to_email="a@example.com", subject="hi", body="b", start_date=date(2030, 1, 1), end_date=date(2030, 1, 2))
    EmailJobCreate(**base)
    for bad in ({"subject": "a\r\nBcc: x@y.com"}, {"subject": "s" * 201}, {"body": "b" * 10001}):
        with pytest.raises(ValidationError):
            EmailJobCreate(**{**base, **bad})


def test_email_job_creation_is_capped_per_org(monkeypatch):
    import asyncio
    import pytest
    from datetime import date
    from fastapi import HTTPException
    from email_scheduler import service
    from email_scheduler.schemas import EmailJobCreate
    payload = EmailJobCreate(organization_id="o", to_email="a@example.com", subject="hi", body="b", start_date=date(2030, 1, 1), end_date=date(2030, 1, 2))
    jobs = [{"status": "active"} for _ in range(service.MAX_ACTIVE_EMAIL_JOBS_PER_ORG)]
    created = []
    monkeypatch.setattr(service.repository, "list_jobs", lambda org: jobs)
    monkeypatch.setattr(service.repository, "create_job", lambda data: created.append(data) or data)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.create_scheduled_job(payload, "org1"))
    assert exc.value.status_code == 429 and created == []
    jobs.pop()
    asyncio.run(service.create_scheduled_job(payload, "org1"))
    assert len(created) == 1


def test_header_value_helpers_block_injection():
    import pytest
    from config import single_line, validate_recipient
    assert single_line("a\r\nBcc: x@y.com") == "a Bcc: x@y.com"
    assert validate_recipient(" a@example.com ") == "a@example.com"
    for bad in ("a@b.com\nBcc: x@y.com", "a@b.com\r", "nobody", "a@b@c.com", ""):
        with pytest.raises(ValueError):
            validate_recipient(bad)
