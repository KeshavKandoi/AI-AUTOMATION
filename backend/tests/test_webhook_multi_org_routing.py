"""
Regression tests for GitHub webhook organization resolution.

Root cause being tested: multiple organizations can legitimately connect the
same github_repo (no uniqueness constraint, by design), so the webhook
handler must never pick an organization by first-row/.data[0] selection.
Instead, org identity is resolved purely by which organization's own
server-side webhook_secret verifies this specific delivery's HMAC signature.
"""
from unittest.mock import patch, MagicMock

import hmac
import hashlib

from webhooks.routes import _resolve_org_for_webhook
from fastapi import HTTPException


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _fake_result(rows):
    m = MagicMock()
    m.data = rows
    return m


ORG_A = {"id": "org-A", "name": "Org A", "github_repo": "acme/repo", "webhook_secret": "secret-a"}
ORG_B = {"id": "org-B", "name": "Org B", "github_repo": "acme/repo", "webhook_secret": "secret-b"}


def test_resolves_correct_org_when_signed_with_org_b_secret_even_though_org_a_is_first_row():
    body = b'{"repository": {"full_name": "acme/repo"}}'
    signature = _sign(body, "secret-b")

    with patch("webhooks.routes.supabase_admin.table") as mock_table:
        # Org A deliberately placed first in the mocked result set, to prove
        # the resolver does not default to data[0].
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result(
            [ORG_A, ORG_B]
        )
        resolved = _resolve_org_for_webhook(body, signature, "acme/repo")
        assert resolved["id"] == "org-B"


def test_resolves_correct_org_when_signed_with_org_a_secret():
    body = b'{"repository": {"full_name": "acme/repo"}}'
    signature = _sign(body, "secret-a")

    with patch("webhooks.routes.supabase_admin.table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result(
            [ORG_A, ORG_B]
        )
        resolved = _resolve_org_for_webhook(body, signature, "acme/repo")
        assert resolved["id"] == "org-A"


def test_zero_matching_signature_raises_401():
    body = b'{"repository": {"full_name": "acme/repo"}}'
    signature = _sign(body, "some-other-secret-entirely")

    with patch("webhooks.routes.supabase_admin.table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result(
            [ORG_A, ORG_B]
        )
        try:
            _resolve_org_for_webhook(body, signature, "acme/repo")
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 401


def test_no_org_connected_to_repo_raises_404():
    body = b'{"repository": {"full_name": "nobody/repo"}}'
    signature = _sign(body, "irrelevant")

    with patch("webhooks.routes.supabase_admin.table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result([])
        try:
            _resolve_org_for_webhook(body, signature, "nobody/repo")
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 404


def test_duplicate_secret_collision_raises_409_and_does_not_pick_either():
    """Simulates the extremely unlikely case of two orgs sharing an identical
    webhook_secret -- must be rejected outright, never arbitrarily resolved."""
    body = b'{"repository": {"full_name": "acme/repo"}}'
    org_a_dup = {**ORG_A, "webhook_secret": "same-secret"}
    org_b_dup = {**ORG_B, "webhook_secret": "same-secret"}
    signature = _sign(body, "same-secret")

    with patch("webhooks.routes.supabase_admin.table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result(
            [org_a_dup, org_b_dup]
        )
        try:
            _resolve_org_for_webhook(body, signature, "acme/repo")
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 409


def test_missing_signature_header_raises_401_not_crash():
    body = b'{"repository": {"full_name": "acme/repo"}}'

    with patch("webhooks.routes.supabase_admin.table") as mock_table:
        mock_table.return_value.select.return_value.eq.return_value.execute.return_value = _fake_result(
            [ORG_A, ORG_B]
        )
        try:
            _resolve_org_for_webhook(body, None, "acme/repo")
            assert False, "expected HTTPException"
        except HTTPException as e:
            assert e.status_code == 401


def _phase4_client(monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from webhooks import routes

    async def fake_execute(job):
        return {"status": "success"}

    monkeypatch.setattr(routes.commit_repo, "get_job", lambda job_id: {"id": job_id, "organization_id": __import__("config").settings.TEST_ORG_ID})
    monkeypatch.setattr(routes.commit_service, "execute_job", fake_execute)
    return TestClient(app)


def test_phase4_webhook_header_secret_accepted(monkeypatch):
    from config import settings
    client = _phase4_client(monkeypatch)
    res = client.post("/webhooks/commit-jobs/abc", headers={"X-Webhook-Secret": settings.GENERIC_WEBHOOK_SECRET})
    assert res.status_code == 200


def test_phase4_webhook_invalid_and_missing_secret_rejected(monkeypatch):
    client = _phase4_client(monkeypatch)
    assert client.post("/webhooks/commit-jobs/abc", headers={"X-Webhook-Secret": "wrong"}).status_code == 401
    assert client.post("/webhooks/commit-jobs/abc").status_code == 401


def test_phase4_webhook_query_secret_fallback_toggle(monkeypatch):
    from config import settings
    client = _phase4_client(monkeypatch)
    monkeypatch.setattr(settings, "ALLOW_QUERY_WEBHOOK_SECRET", True)
    assert client.post("/webhooks/commit-jobs/abc", params={"secret": settings.GENERIC_WEBHOOK_SECRET}).status_code == 200
    monkeypatch.setattr(settings, "ALLOW_QUERY_WEBHOOK_SECRET", False)
    assert client.post("/webhooks/commit-jobs/abc", params={"secret": settings.GENERIC_WEBHOOK_SECRET}).status_code == 401


def test_phase4_webhook_secret_not_logged(monkeypatch, caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    client = _phase4_client(monkeypatch)
    client.post("/webhooks/commit-jobs/abc", headers={"X-Webhook-Secret": "sentinel-secret-value"})
    assert "sentinel-secret-value" not in caplog.text


def test_phase4_github_webhook_invalid_json_returns_400():
    from fastapi.testclient import TestClient
    from main import app
    res = TestClient(app).post("/webhooks/github", content=b"not-json", headers={"Content-Type": "application/json"})
    assert res.status_code == 400
