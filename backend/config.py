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

    class Config:
        env_file = ".env"

settings = Settings()

logging.basicConfig(
    level=logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_coo")

supabase_admin = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
