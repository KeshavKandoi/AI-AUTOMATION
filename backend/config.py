import logging
from pydantic_settings import BaseSettings
from supabase import create_client
from google import genai

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str
    GEMINI_API_KEY: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    GOOGLE_GMAIL_REDIRECT_URI: str
    GOOGLE_CALENDAR_REDIRECT_URI: str
    DISCORD_WEBHOOK_URL: str
    TEST_GITHUB_ACCESS_TOKEN: str
    TEST_ORG_ID: str
    ENVIRONMENT: str = "development"
    TOKEN_ENCRYPTION_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()

from cryptography.fernet import Fernet
fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())

def encrypt_token(token: str) -> str:
    if not token:
        return token
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(token: str) -> str:
    if not token:
        return token
    return fernet.decrypt(token.encode()).decode()

logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_coo")

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)

supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

import httpx
from datetime import datetime, timezone

def get_valid_access_token(integration_id: str) -> str:
    result = supabase_admin.table("oauth_tokens").select("*").eq("integration_id", integration_id).order("created_at", desc=True).limit(1).execute()
    if not result.data:
        raise ValueError(f"No token found for integration_id {integration_id}")

    row = result.data[0]
    access_token = decrypt_token(row["access_token"])
    expires_at = row.get("expires_at")
    refresh_token_encrypted = row.get("refresh_token")

    is_expired = False
    if expires_at:
        expiry_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) >= expiry_dt:
            is_expired = True

    if not is_expired:
        return access_token

    if not refresh_token_encrypted:
        raise ValueError("Token expired and no refresh_token available — user must re-login")

    refresh_token = decrypt_token(refresh_token_encrypted)

    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
    )
    token_data = response.json()
    new_access_token = token_data.get("access_token")

    if not new_access_token:
        raise ValueError(f"Failed to refresh token: {token_data}")

    from datetime import timedelta
    new_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3599))).isoformat()

    supabase_admin.table("oauth_tokens").update({
        "access_token": encrypt_token(new_access_token),
        "expires_at": new_expires_at
    }).eq("id", row["id"]).execute()

    logger.info(f"Refreshed access token for integration_id {integration_id}")
    return new_access_token
