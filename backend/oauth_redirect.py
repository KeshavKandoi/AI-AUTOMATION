"""Safe, configured return URL for browser-based integration callbacks."""

from urllib.parse import urlencode

from fastapi import HTTPException

from config import settings


def is_browser_navigation(accept: str | None, fetch_mode: str | None) -> bool:
    """OAuth redirects are top-level navigations even with JSON viewer extensions."""
    return fetch_mode == "navigate" or isinstance(accept, str) and "text/html" in accept


def google_callback_uri(provider: str) -> str:
    """Use this Render service's URL so an old callback setting cannot point elsewhere."""
    if provider not in {"gmail", "calendar"}:
        raise ValueError("Unsupported Google provider")
    service_url = settings.RENDER_EXTERNAL_URL.strip().rstrip("/")
    if service_url:
        return f"{service_url}/{provider}/callback"
    return (
        settings.GOOGLE_GMAIL_REDIRECT_URI if provider == "gmail"
        else settings.GOOGLE_CALENDAR_REDIRECT_URI
    )


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
