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
