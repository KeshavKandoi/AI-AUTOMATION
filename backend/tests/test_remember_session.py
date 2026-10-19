from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from auth import service
from main import app


def test_login_and_refresh_keep_session_for_30_days(monkeypatch):
    monkeypatch.setattr(service, "login", lambda *_: ({"id": "user-1"}, "access", "refresh-1"))
    monkeypatch.setattr(service, "refresh_session", lambda *_: ("access-2", "refresh-2", {"id": "user-1"}))
    client = TestClient(app)

    login = client.post("/auth/login", json={
        "email": "test@example.com", "password": "password",
    })
    assert login.status_code == 200
    cookies = login.headers.get_list("set-cookie")
    assert len(cookies) == 1
    assert "max-age=2592000" in cookies[0].lower()

    refresh = client.post("/auth/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["access_token"] == "access-2"
    assert "max-age=2592000" in refresh.headers.get_list("set-cookie")[0].lower()

    logout = client.post("/auth/logout")
    assert logout.status_code == 200
    assert len(logout.headers.get_list("set-cookie")) == 2
    assert client.post("/auth/refresh").status_code == 401


def test_refresh_outage_does_not_report_expired_session(monkeypatch):
    client = MagicMock()
    client.auth.refresh_session.side_effect = ConnectionError("temporarily unavailable")
    monkeypatch.setattr(service, "get_auth_client", lambda: client)

    with pytest.raises(HTTPException) as error:
        service.refresh_session("refresh-token")

    assert error.value.status_code == 503

