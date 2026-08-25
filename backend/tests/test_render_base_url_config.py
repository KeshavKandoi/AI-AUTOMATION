"""
Regression test: RENDER_BASE_URL must be read from settings/config, not
hardcoded in main.py, and /github/connect-repo must actually pass that
configured value through to register_github_webhook.
"""
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


def test_render_base_url_is_in_settings():
    from config import settings
    assert hasattr(settings, "RENDER_BASE_URL")
    assert settings.RENDER_BASE_URL.startswith("https://")


def test_main_module_has_no_hardcoded_render_base_url_constant():
    import main
    assert not hasattr(main, "RENDER_BASE_URL")


def test_connect_repo_uses_configured_base_url():
    from main import app
    from auth.dependencies import get_current_org_id

    with patch("main.supabase_admin") as sb, \
         patch("main.register_github_webhook", new_callable=AsyncMock) as mock_register, \
         patch("closeout._resolve_access_token", return_value="tok"), \
         patch("main.settings") as mock_settings:

        mock_settings.RENDER_BASE_URL = "https://custom-configured-url.example.com"
        mock_register.return_value = {"id": "hook-1"}
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        client = TestClient(app)
        res = client.post("/github/connect-repo", params={"org_id": "org-1", "repo_full_name": "acme/repo"})

        assert res.status_code == 200
        called_kwargs = mock_register.call_args.kwargs
        assert called_kwargs["base_url"] == "https://custom-configured-url.example.com"
