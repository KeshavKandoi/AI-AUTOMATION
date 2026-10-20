import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

from fastapi import Request

import discord_oauth


WEBHOOK = "https://discord.com/api/webhooks/123456789012345678/example-token"


def test_discord_login_requests_channel_webhook_permission():
    with patch.object(discord_oauth.settings, "DISCORD_CLIENT_ID", "app-id"), \
         patch.object(discord_oauth.settings, "DISCORD_CLIENT_SECRET", "secret"), \
         patch.object(discord_oauth.settings, "DISCORD_REDIRECT_URI", "https://backend.example.com/discord/callback"), \
         patch.object(discord_oauth, "_issue_oauth_state", return_value="single-use-state"):
        url = discord_oauth.discord_login("org-a")["url"]

    query = parse_qs(urlparse(url).query)
    assert query["scope"] == ["webhook.incoming"]
    assert query["state"] == ["single-use-state"]
    assert query["redirect_uri"] == ["https://backend.example.com/discord/callback"]


def test_discord_callback_saves_webhook_for_state_organization():
    response = MagicMock()
    response.json.return_value = {"webhook": {"url": WEBHOOK}}
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    table = MagicMock()
    table.update.return_value.eq.return_value.select.return_value.execute.return_value.data = [{"id": "org-a"}]
    request = Request({"type": "http", "method": "GET", "path": "/discord/callback", "headers": []})

    with patch.object(discord_oauth.settings, "DISCORD_CLIENT_ID", "app-id"), \
         patch.object(discord_oauth.settings, "DISCORD_CLIENT_SECRET", "secret"), \
         patch.object(discord_oauth.settings, "DISCORD_REDIRECT_URI", "https://backend.example.com/discord/callback"), \
         patch.object(discord_oauth, "_consume_oauth_state", return_value="org-a"), \
         patch.object(discord_oauth.httpx, "AsyncClient", return_value=client), \
         patch.object(discord_oauth.supabase_admin, "table", return_value=table):
        result = asyncio.run(discord_oauth.discord_callback(request, code="code", state="state"))

    assert result == {"status": "connected"}
    table.update.assert_called_once_with({"discord_webhook_url": WEBHOOK})
    table.update.return_value.eq.assert_called_once_with("id", "org-a")
