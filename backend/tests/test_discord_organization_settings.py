import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import workflow_engine
from auth.dependencies import get_current_org_id
from config import pick_discord_webhook, resolve_discord_webhook, settings, supabase_admin
from main import app


VALID_WEBHOOK = "https://discord.com/api/webhooks/123456789012345678/placeholder-token"


@pytest.fixture(autouse=True)
def _org_scope():
    app.dependency_overrides[get_current_org_id] = lambda: "org-a"
    yield
    app.dependency_overrides.clear()


def test_saved_org_webhook_is_masked_and_used(monkeypatch):
    row = {"discord_webhook_url": VALID_WEBHOOK}
    query = MagicMock()
    query.execute.return_value = MagicMock(data=[row])
    table = MagicMock()
    table.select.return_value.eq.return_value = query
    monkeypatch.setattr(supabase_admin, "table", lambda name: table)

    response = TestClient(app).get("/organization-settings/discord-webhook?org_id=org-b")
    assert response.status_code == 200
    assert response.json() == {
        "configured": True,
        "masked_url": "Discord webhook ••••••••",
        "source": "settings",
    }
    assert "placeholder-token" not in response.text
    table.select.return_value.eq.assert_called_with("id", "org-a")

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            assert url == VALID_WEBHOOK
            return MagicMock(status_code=204)

        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr(workflow_engine.httpx, "AsyncClient", Client)
    result = asyncio.run(workflow_engine._action_notify_discord("org-a", {"title": "test"}))
    assert result == {"status": "sent"}


def test_missing_webhook_has_useful_setup_message(monkeypatch):
    query = MagicMock()
    query.execute.return_value = MagicMock(data=[{"discord_webhook_url": None}])
    table = MagicMock()
    table.select.return_value.eq.return_value = query
    monkeypatch.setattr(supabase_admin, "table", lambda name: table)

    response = TestClient(app).get("/organization-settings/discord-webhook")
    assert response.status_code == 200
    assert response.json() == {"configured": False, "masked_url": None, "source": None}
    with pytest.raises(RuntimeError, match="add one in Settings"):
        asyncio.run(workflow_engine._action_notify_discord("org-a", {"title": "test"}))


def test_deleted_organization_cannot_use_environment_fallback(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_ENV_ORG_ID", "org-a")
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", VALID_WEBHOOK)
    query = MagicMock()
    query.execute.return_value = MagicMock(data=[])
    table = MagicMock()
    table.select.return_value.eq.return_value = query
    monkeypatch.setattr(supabase_admin, "table", lambda _name: table)
    with pytest.raises(RuntimeError, match="organization is unavailable"):
        asyncio.run(workflow_engine._action_notify_discord("org-a", {"title": "test"}))


def test_production_fallback_is_scoped_to_configured_organization(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DISCORD_ENV_ORG_ID", "org-a")
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", VALID_WEBHOOK)
    assert pick_discord_webhook("org-a", None) == VALID_WEBHOOK
    assert pick_discord_webhook("org-b", None) is None


def test_environment_fallback_requires_explicit_org_id_and_valid_url(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", VALID_WEBHOOK)
    monkeypatch.setattr(settings, "DISCORD_ENV_ORG_ID", "")
    assert pick_discord_webhook("org-a", None) is None
    monkeypatch.setattr(settings, "DISCORD_ENV_ORG_ID", "org-a")
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", "https://example.invalid/api/webhooks/1/private-token")
    assert pick_discord_webhook("org-a", None) is None


def test_saved_org_webhook_overrides_environment(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DISCORD_ENV_ORG_ID", "org-a")
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", VALID_WEBHOOK)
    saved = "https://discord.com/api/webhooks/234567890123456789/saved-placeholder"
    assert resolve_discord_webhook("org-a", saved) == (saved, "settings")


def test_status_uses_effective_environment_without_exposing_secret(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DISCORD_ENV_ORG_ID", "org-a")
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", VALID_WEBHOOK)
    query = MagicMock()
    query.execute.return_value = MagicMock(data=[{"discord_webhook_url": None}])
    table = MagicMock()
    table.select.return_value.eq.return_value = query
    monkeypatch.setattr(supabase_admin, "table", lambda name: table)

    response = TestClient(app).get("/organization-settings/discord-webhook")
    assert response.status_code == 200
    assert response.json() == {
        "configured": True,
        "masked_url": "Discord webhook ••••••••",
        "source": "environment",
    }
    assert "placeholder-token" not in response.text

    app.dependency_overrides[get_current_org_id] = lambda: "org-b"
    other_org_response = TestClient(app).get("/organization-settings/discord-webhook")
    assert other_org_response.json() == {"configured": False, "masked_url": None, "source": None}
    table.select.return_value.eq.assert_called_with("id", "org-b")


def test_removing_saved_webhook_restores_matching_environment_status(monkeypatch):
    monkeypatch.setattr(settings, "DISCORD_ENV_ORG_ID", "org-a")
    monkeypatch.setattr(settings, "DISCORD_WEBHOOK_URL", VALID_WEBHOOK)
    update = MagicMock()
    update.select.return_value.execute.return_value = MagicMock(data=[{"id": "org-a"}])
    table = MagicMock()
    table.update.return_value.eq.return_value = update
    monkeypatch.setattr(supabase_admin, "table", lambda name: table)

    response = TestClient(app).put("/organization-settings/discord-webhook", json={"webhook_url": None})
    assert response.status_code == 200
    assert response.json() == {
        "configured": True,
        "masked_url": "Discord webhook ••••••••",
        "source": "environment",
    }
    assert "placeholder-token" not in response.text
    table.update.assert_called_once_with({"discord_webhook_url": None})


def test_invalid_url_is_rejected_without_echoing_or_saving(monkeypatch):
    update = MagicMock()
    table = MagicMock()
    table.update.return_value.eq.return_value = update
    monkeypatch.setattr(supabase_admin, "table", lambda name: table)

    response = TestClient(app).put(
        "/organization-settings/discord-webhook",
        json={"webhook_url": "https://example.invalid/webhook/private-token"},
    )
    assert response.status_code == 422
    assert "private-token" not in response.text
    table.update.assert_not_called()


def test_settings_update_is_bound_to_authenticated_organization(monkeypatch):
    update = MagicMock()
    update.select.return_value.execute.return_value = MagicMock(data=[{"id": "org-a"}])
    table = MagicMock()
    table.update.return_value.eq.return_value = update
    monkeypatch.setattr(supabase_admin, "table", lambda name: table)

    response = TestClient(app).put(
        "/organization-settings/discord-webhook?org_id=org-b",
        json={"webhook_url": VALID_WEBHOOK},
    )
    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert response.json()["source"] == "settings"
    table.update.return_value.eq.assert_called_once_with("id", "org-a")
    assert "placeholder-token" not in response.text


def test_discord_http_failure_is_reported_without_webhook_secret(monkeypatch):
    query = MagicMock()
    query.execute.return_value = MagicMock(data=[{"discord_webhook_url": VALID_WEBHOOK}])
    table = MagicMock()
    table.select.return_value.eq.return_value = query
    monkeypatch.setattr(supabase_admin, "table", lambda name: table)

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return MagicMock(status_code=500)

        def __init__(self, **_kwargs):
            pass

    monkeypatch.setattr(workflow_engine.httpx, "AsyncClient", Client)
    with pytest.raises(RuntimeError, match="status 500") as error:
        asyncio.run(workflow_engine._action_notify_discord("org-a", {"title": "test"}))
    assert "placeholder-token" not in str(error.value)


def test_discord_failure_keeps_other_workflow_actions_successful(monkeypatch):
    calls = []

    async def successful_action(org_id, context):
        calls.append(org_id)
        return {"status": "ok"}

    monkeypatch.setattr(workflow_engine, "_org_run_budget_exceeded", lambda _org: False)
    monkeypatch.setattr(workflow_engine, "log_event", lambda **_kwargs: None)
    monkeypatch.setattr(workflow_engine.supabase_admin, "table", lambda name: _workflow_table(name))
    monkeypatch.setattr(workflow_engine, "ACTION_REGISTRY", {
        "create_task": successful_action,
        "send_email": successful_action,
        "notify_discord": lambda *_args: _raise_discord_error(),
        "save_audit_log": successful_action,
    })

    result = asyncio.run(workflow_engine.execute_workflow({
        "id": "workflow-1", "organization_id": "org-a", "name": "High",
        "conditions": {},
        "actions": ["create_task", "send_email", "notify_discord", "save_audit_log"],
    }, {"title": "test"}))

    assert result["status"] == "partial_failure"
    executed = result["actions_executed"]
    assert [item["action"] for item in executed] == [
        "create_task", "send_email", "notify_discord", "save_audit_log",
    ]
    assert executed[0]["result"] == {"status": "ok"}
    assert executed[1]["result"] == {"status": "ok"}
    assert executed[2]["error"].startswith("Discord webhook")
    assert executed[3]["result"] == {"status": "ok"}
    assert len(calls) == 3


def _raise_discord_error():
    raise RuntimeError("Discord webhook is not configured for this organization")


def _workflow_table(name):
    table = MagicMock()
    if name == "workflow_runs":
        table.insert.return_value.execute.return_value = MagicMock(data=[{
            "status": "partial_failure",
            "actions_executed": [
                {"action": "create_task", "result": {"status": "ok"}},
                {"action": "send_email", "result": {"status": "ok"}},
                {"action": "notify_discord", "error": "Discord webhook is not configured for this organization"},
                {"action": "save_audit_log", "result": {"status": "ok"}},
            ],
        }])
    return table
