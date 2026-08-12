"""Verifies /gmail/login and /calendar/login build correct authorization
URLs for both first-time (no refresh token) and returning (has refresh
token) users — without hitting Google or the real database, and without
printing any secret values."""
from unittest.mock import MagicMock
from urllib.parse import urlparse, parse_qs

import config
import main

TEST_ORG = "test-org-verify-oauth"

def make_supabase_mock(has_refresh_token: bool):
    mock = MagicMock()
    integrations_result = MagicMock()
    integrations_result.data = [{"id": "fake-integration-id"}]
    tokens_result = MagicMock()
    tokens_result.data = [{"refresh_token": "fake-encrypted-value" if has_refresh_token else None}]

    def table_side_effect(name):
        chain = MagicMock()
        if name == "integrations":
            chain.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = integrations_result
        elif name == "oauth_tokens":
            chain.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = tokens_result
        return chain

    mock.table.side_effect = table_side_effect
    return mock

def check(provider: str, login_path: str, expected_scope_fragment: str, expected_redirect_env: str, has_refresh_token: bool):
    main.supabase_admin = make_supabase_mock(has_refresh_token)
    from fastapi.testclient import TestClient
    client = TestClient(main.app, follow_redirects=False)
    resp = client.get(login_path, params={"org_id": TEST_ORG})

    assert resp.status_code in (302, 307), f"{provider}: expected redirect, got {resp.status_code}"
    location = resp.headers["location"]
    parsed = urlparse(location)
    qs = parse_qs(parsed.query)

    assert parsed.netloc == "accounts.google.com", f"{provider}: wrong host {parsed.netloc}"
    assert qs.get("client_id", [""])[0] == config.settings.GOOGLE_CLIENT_ID, f"{provider}: client_id mismatch"
    assert qs.get("redirect_uri", [""])[0] == getattr(config.settings, expected_redirect_env), f"{provider}: redirect_uri mismatch"
    assert expected_scope_fragment in qs.get("scope", [""])[0], f"{provider}: scope missing {expected_scope_fragment}"
    assert qs.get("access_type", [""])[0] == "offline", f"{provider}: access_type not offline"
    assert qs.get("state", [""])[0] == TEST_ORG, f"{provider}: state mismatch"

    has_prompt = "prompt" in qs
    expected_prompt = not has_refresh_token
    assert has_prompt == expected_prompt, (
        f"{provider}: prompt=consent presence wrong "
        f"(has_refresh_token={has_refresh_token}, prompt_present={has_prompt})"
    )

    scenario = "returning user (has refresh token)" if has_refresh_token else "first-time user (no refresh token)"
    prompt_state = "prompt=consent OMITTED (correct)" if has_refresh_token else "prompt=consent PRESENT (correct)"
    print(f"[PASS] {provider} / {scenario}: {prompt_state}")

check("gmail", "/gmail/login", "gmail.readonly", "GOOGLE_GMAIL_REDIRECT_URI", has_refresh_token=False)
check("gmail", "/gmail/login", "gmail.readonly", "GOOGLE_GMAIL_REDIRECT_URI", has_refresh_token=True)
check("calendar", "/calendar/login", "auth/calendar", "GOOGLE_CALENDAR_REDIRECT_URI", has_refresh_token=False)
check("calendar", "/calendar/login", "auth/calendar", "GOOGLE_CALENDAR_REDIRECT_URI", has_refresh_token=True)

print("\\nAll checks passed. No secrets were printed, no network calls to Google were made, no real database rows were touched.")
