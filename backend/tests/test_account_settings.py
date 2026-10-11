from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthInvalidCredentialsError
from postgrest.exceptions import APIError

from account import service as account_service
from auth import service as auth_service
from auth.dependencies import get_current_user
from main import app


def _auth_client(user_id="user-1"):
    client = MagicMock()
    client.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id=user_id)
    )
    return client


def test_change_password_confirms_new_login(monkeypatch):
    current, admin, confirmation = (_auth_client() for _ in range(3))
    monkeypatch.setattr(auth_service, "get_auth_client", MagicMock(side_effect=[current, admin, confirmation]))

    auth_service.change_password("user-1", "test@example.com", "old-placeholder", "new-placeholder")

    current.auth.sign_in_with_password.assert_called_once_with({
        "email": "test@example.com", "password": "old-placeholder"
    })
    admin.auth.admin.update_user_by_id.assert_called_once_with("user-1", {"password": "new-placeholder"})
    confirmation.auth.sign_in_with_password.assert_called_once_with({
        "email": "test@example.com", "password": "new-placeholder"
    })


def test_change_password_distinguishes_invalid_password_from_auth_outage(monkeypatch):
    client = _auth_client()
    client.auth.sign_in_with_password.side_effect = AuthInvalidCredentialsError("invalid")
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: client)
    with pytest.raises(HTTPException) as error:
        auth_service.change_password("user-1", "test@example.com", "wrong", "new-placeholder")
    assert error.value.status_code == 401
    assert error.value.detail == "Current password is incorrect"
    client.auth.admin.update_user_by_id.assert_not_called()

    client.auth.sign_in_with_password.side_effect = ConnectionError("down")
    with pytest.raises(HTTPException) as error:
        auth_service.change_password("user-1", "test@example.com", "old-placeholder", "new-placeholder")
    assert error.value.status_code == 502
    assert "unavailable" in error.value.detail


def test_email_code_reset_updates_and_verifies_password(monkeypatch):
    admin, confirmation = _auth_client(), _auth_client()
    monkeypatch.setattr(auth_service, "get_auth_client", MagicMock(side_effect=[admin, confirmation]))
    monkeypatch.setattr(auth_service, "_verify_otp", lambda *_args: True)
    monkeypatch.setattr(auth_service.repository, "get_user_profile_by_email", lambda _email: {"id": "user-1"})

    auth_service.reset_password("test@example.com", "000000", "new-placeholder")

    admin.auth.admin.update_user_by_id.assert_called_once_with("user-1", {"password": "new-placeholder"})
    confirmation.auth.sign_in_with_password.assert_called_once()


def test_password_update_or_verification_failure_never_reports_success(monkeypatch):
    admin = _auth_client()
    admin.auth.admin.update_user_by_id.side_effect = ConnectionError("down")
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: admin)
    with pytest.raises(HTTPException) as error:
        auth_service._update_and_confirm_password("user-1", "test@example.com", "new-placeholder")
    assert error.value.status_code == 502
    assert "Could not update" in error.value.detail

    admin.auth.admin.update_user_by_id.side_effect = None
    confirmation = _auth_client("another-user")
    monkeypatch.setattr(auth_service, "get_auth_client", MagicMock(side_effect=[admin, confirmation]))
    with pytest.raises(HTTPException) as error:
        auth_service._update_and_confirm_password("user-1", "test@example.com", "new-placeholder")
    assert error.value.status_code == 502
    assert "may have succeeded" in error.value.detail


class FakeQuery:
    def __init__(self, db, table):
        self.db, self.table, self.operation = db, table, ""
        self.filters = []

    def select(self, *_args, **_kwargs):
        if not self.operation:
            self.operation = "select"
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def update(self, _payload):
        self.operation = "update"
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, _value):
        return self

    def in_(self, _field, _values):
        return self

    def execute(self):
        self.db.calls.append((self.table, self.operation, tuple(self.filters)))
        if self.table == "user_profiles" and self.operation == "select":
            return SimpleNamespace(data=[{"id": uid} for uid in self.db.members])
        if self.table == "user_profiles" and self.operation == "delete":
            return SimpleNamespace(data=[{"id": "user-1"}])
        if self.table == "organizations" and self.operation == "delete":
            return SimpleNamespace(data=[{"id": "org-1"}])
        return SimpleNamespace(data=[])


class FakeDB:
    def __init__(self, members):
        self.members, self.calls = members, []

    def table(self, name):
        return FakeQuery(self, name)


def _account_setup(monkeypatch, members):
    db = FakeDB(members)
    auth = _auth_client()
    auth.auth.sign_in_with_password.side_effect = [
        SimpleNamespace(user=SimpleNamespace(id="user-1")),
        AuthInvalidCredentialsError("invalid"),
    ]
    monkeypatch.setattr(account_service, "supabase_admin", db)
    monkeypatch.setattr(account_service, "get_auth_client", lambda: auth)
    monkeypatch.setattr(account_service.auth_repository, "get_user_profile", lambda _id: {
        "id": "user-1", "email": "test@example.com", "organization_id": "org-1"
    })
    return db, auth


def test_shared_org_account_deletion_preserves_other_members_data(monkeypatch):
    db, auth = _account_setup(monkeypatch, ["user-1", "user-2"])
    account_service.delete_account("user-1", "test@example.com", "placeholder")

    deleted_tables = {table for table, action, _ in db.calls if action == "delete"}
    assert deleted_tables == {"auth_otps", "user_profiles"}
    assert ("audit_logs", "update", (("organization_id", "org-1"), ("user_id", "user-1"))) in db.calls
    auth.auth.admin.delete_user.assert_called_once_with("user-1")


def test_sole_member_deletion_removes_jobs_tokens_and_org(monkeypatch):
    db, auth = _account_setup(monkeypatch, ["user-1"])
    account_service.delete_account("user-1", "test@example.com", "placeholder")

    deleted_tables = {table for table, action, _ in db.calls if action == "delete"}
    assert {"commit_jobs", "email_jobs", "scheduled_commits", "integrations", "organizations"} <= deleted_tables
    auth.auth.admin.delete_user.assert_called_once_with("user-1")


def test_partial_deletion_reports_failure_and_keeps_auth_account(monkeypatch):
    _db, auth = _account_setup(monkeypatch, ["user-1"])
    monkeypatch.setattr(account_service, "_delete_by_org", MagicMock(side_effect=RuntimeError("db failure")))

    with pytest.raises(HTTPException) as error:
        account_service.delete_account("user-1", "test@example.com", "placeholder")
    assert error.value.status_code == 500
    assert "Some data may already be removed" in error.value.detail
    auth.auth.admin.delete_user.assert_not_called()


def test_account_deletion_fails_if_auth_still_allows_login(monkeypatch):
    _db, auth = _account_setup(monkeypatch, ["user-1", "user-2"])
    auth.auth.sign_in_with_password.side_effect = [
        SimpleNamespace(user=SimpleNamespace(id="user-1")),
        SimpleNamespace(user=SimpleNamespace(id="user-1")),
    ]
    with pytest.raises(HTTPException) as error:
        account_service.delete_account("user-1", "test@example.com", "placeholder")
    assert error.value.status_code == 500
    assert "authentication verification" in error.value.detail


def test_missing_legacy_table_is_skipped_but_other_errors_stop_deletion(monkeypatch):
    def missing(_table, _org):
        raise APIError({"code": "PGRST205", "message": "missing table"})

    monkeypatch.setattr(account_service, "_delete_by_org", missing)
    account_service._delete_optional_legacy_by_org("job_hunter_gmail_events", "org-1")

    def broken(_table, _org):
        raise APIError({"code": "42501", "message": "permission denied"})

    monkeypatch.setattr(account_service, "_delete_by_org", broken)
    with pytest.raises(APIError):
        account_service._delete_optional_legacy_by_org("job_hunter_gmail_events", "org-1")


def test_account_delete_endpoint_requires_authentication():
    assert TestClient(app).post("/account/delete", json={"password": "placeholder"}).status_code == 401


def test_change_password_endpoint_does_not_echo_password(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: {"sub": "user-1", "email": "test@example.com"}
    monkeypatch.setattr(auth_service, "change_password", MagicMock(side_effect=HTTPException(status_code=401, detail="Current password is incorrect")))
    try:
        response = TestClient(app).post("/auth/change-password", json={
            "current_password": "private-old", "new_password": "private-new"
        })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
    assert "private-old" not in response.text
    assert "private-new" not in response.text
