import re

with open("main.py", "r") as f:
    content = f.read()

old_gmail = '''@app.get("/gmail/login")
def gmail_login(org_id: str):
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_GMAIL_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send"
        f"&access_type=offline&prompt=consent&state={org_id}"
    )
    return RedirectResponse(url)'''

new_gmail = '''def _has_stored_refresh_token(org_id: str, provider: str) -> bool:
    """Checks whether this organization already has a connected integration
    with a stored (encrypted) refresh_token for the given provider. Used
    only to decide whether /login needs to force Google's consent screen —
    never decrypts or exposes the token itself."""
    integration_res = supabase_admin.table("integrations") \\
        .select("id") \\
        .eq("organization_id", org_id) \\
        .eq("provider", provider) \\
        .eq("connected", True) \\
        .order("created_at", desc=True) \\
        .limit(1) \\
        .execute()
    if not integration_res.data:
        return False
    integration_id = integration_res.data[0]["id"]
    token_res = supabase_admin.table("oauth_tokens") \\
        .select("refresh_token") \\
        .eq("integration_id", integration_id) \\
        .order("created_at", desc=True) \\
        .limit(1) \\
        .execute()
    if not token_res.data:
        return False
    return bool(token_res.data[0].get("refresh_token"))


@app.get("/gmail/login")
def gmail_login(org_id: str):
    prompt_param = "" if _has_stored_refresh_token(org_id, "gmail") else "&prompt=consent"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_GMAIL_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send"
        f"&access_type=offline{prompt_param}&state={org_id}"
    )
    return RedirectResponse(url)'''

old_calendar = '''@app.get("/calendar/login")
def calendar_login(org_id: str):
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_CALENDAR_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/calendar"
        f"&access_type=offline&prompt=consent&state={org_id}"
    )
    return RedirectResponse(url)'''

new_calendar = '''@app.get("/calendar/login")
def calendar_login(org_id: str):
    prompt_param = "" if _has_stored_refresh_token(org_id, "calendar") else "&prompt=consent"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_CALENDAR_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=https://www.googleapis.com/auth/calendar"
        f"&access_type=offline{prompt_param}&state={org_id}"
    )
    return RedirectResponse(url)'''

assert content.count(old_gmail) == 1, f"gmail_login match count: {content.count(old_gmail)} (expected 1)"
assert content.count(old_calendar) == 1, f"calendar_login match count: {content.count(old_calendar)} (expected 1)"

content = content.replace(old_gmail, new_gmail)
content = content.replace(old_calendar, new_calendar)

with open("main.py", "w") as f:
    f.write(content)

print("Patch applied successfully.")
