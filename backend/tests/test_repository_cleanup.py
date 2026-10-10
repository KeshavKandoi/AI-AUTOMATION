"""Regression checks for OTP delivery, scheduler isolation, and removed access."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from auth import service
from auth.routes import refresh_cookie_kwargs
from config import settings
import scheduler

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("failure", [False, RuntimeError("provider unavailable")])
def test_failed_otp_delivery_consumes_hash_and_reports_error(monkeypatch, failure):
    consumed = []
    monkeypatch.setattr(service.repository, "get_latest_otp", lambda *_: None)
    monkeypatch.setattr(service.repository, "create_otp", lambda *_: {"id": "otp-1"})
    monkeypatch.setattr(service.repository, "mark_otp_consumed", lambda otp_id: consumed.append(otp_id) or True)
    def send(*_):
        if isinstance(failure, Exception):
            raise failure
        return failure
    monkeypatch.setattr(service, "send_otp_email", send)
    with pytest.raises(HTTPException) as exc:
        service._issue_otp("a@example.com", "signup")
    assert exc.value.status_code == 502
    assert consumed == ["otp-1"]


def test_signup_uses_direct_profile_lookup(monkeypatch):
    auth = MagicMock()
    auth.auth.admin.get_user_by_id.return_value.user.email_confirmed_at = "2026-01-01"
    lookup = MagicMock(return_value={"id": "user-1"})
    monkeypatch.setattr(service.repository, "get_user_profile_by_email", lookup)
    monkeypatch.setattr(service, "get_auth_client", lambda: auth)
    assert service.signup("Name", "a@example.com", "password", "Org") == "a@example.com"
    lookup.assert_called_once_with("a@example.com")
    auth.auth.admin.create_user.assert_not_called()
    auth.auth.admin.list_users.assert_not_called()


def test_scheduler_requires_explicit_production_target(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SCHEDULER_ORG_ID", "org-1")
    monkeypatch.setattr(settings, "SCHEDULER_REPOSITORY", "acme/repo")
    monkeypatch.setattr(settings, "SCHEDULER_ENABLE_PRODUCTION", False)
    assert scheduler.scheduler_target() is None
    monkeypatch.setattr(settings, "SCHEDULER_ENABLE_PRODUCTION", True)
    assert scheduler.scheduler_target() == ("org-1", "acme/repo")
    monkeypatch.setattr(settings, "SCHEDULER_REPOSITORY", "")
    assert scheduler.scheduler_target() is None


def test_refresh_cookie_is_http_compatible_locally_and_secure_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    assert refresh_cookie_kwargs()["secure"] is False
    assert refresh_cookie_kwargs()["samesite"] == "lax"
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert refresh_cookie_kwargs()["secure"] is True
    assert refresh_cookie_kwargs()["samesite"] == "none"


def test_public_security_page_and_removed_feature_references():
    client = (ROOT / "ai-coo-frontend/src/api/client.ts").read_text()
    assert "'/security'" in client
    source_files = list((ROOT / "ai-coo-frontend/src").rglob("*.ts")) + list((ROOT / "ai-coo-frontend/src").rglob("*.tsx"))
    source = "\n".join(p.read_text() for p in source_files)
    assert "importEmail" not in source
    assert "/integrations/calendar" not in source
    assert "create_calendar_event" not in source
