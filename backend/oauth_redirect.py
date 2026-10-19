"""Safe, configured return URL for browser-based integration callbacks."""

from urllib.parse import urlencode

from fastapi import HTTPException

from config import settings


def integration_return_url(provider: str, result: str) -> str:
    allowed_origins = [
        origin.strip().rstrip("/")
        for origin in settings.ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]
    frontend_url = settings.FRONTEND_URL.strip().rstrip("/") or (
        allowed_origins[0] if allowed_origins else ""
    )
    if frontend_url not in allowed_origins:
        raise HTTPException(status_code=503, detail="Frontend redirect URL is not configured")
    return f"{frontend_url}/integrations?{urlencode({'integration': provider, 'status': result})}"
