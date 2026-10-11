"""Gmail and removed-feature security regression tests."""
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse
from fastapi.testclient import TestClient
from main import app, gmail_login

ROOT = Path(__file__).resolve().parents[2]


def test_gmail_scope_is_send_and_email_only(monkeypatch):
    monkeypatch.setattr("main._issue_oauth_state", lambda org, provider: "state")
    scopes = parse_qs(urlparse(gmail_login("org")["url"]).query)["scope"][0].split()
    assert scopes == ["https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/userinfo.email"]


def test_removed_routes_are_unavailable():
    client = TestClient(app)
    for path in ("/calendar/login", "/calendar/callback", "/calendar/events", "/calendar/summary", "/calendar/create-event", "/job-hunter/import-email"):
        assert client.get(path).status_code in (404, 405)
        assert client.post(path).status_code in (404, 405)


def test_gmail_does_not_read_inbox():
    files = list((ROOT / "backend").rglob("*.py"))
    production = [p for p in files if "tests" not in p.parts and "venv" not in p.parts]
    source = "\n".join(p.read_text() for p in production)
    assert "gmail.readonly" not in source
    assert "https://www.googleapis.com/auth/calendar" not in source
    assert "users/me/messages/send" in source
    assert not re.search(r"users/me/messages(?!/send)", source)
