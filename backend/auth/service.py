import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from config import settings, supabase_admin, logger
from email_service import send_otp_email
from auth import repository

MAX_OTP_ATTEMPTS = 5


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _issue_otp(email: str, purpose: str) -> str:
    """Enforces resend cooldown, generates + stores a hashed OTP, sends it via Resend."""
    latest = repository.get_latest_otp(email, purpose)
    if latest:
        created_at = datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
        if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
            wait = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(status_code=429, detail=f"Please wait {wait}s before requesting another code")

    otp = _generate_otp()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)).isoformat()
    repository.create_otp(email, _hash_otp(otp), purpose, expires_at)
    sent = send_otp_email(email, otp, purpose)
    if not sent:
        logger.error(f"Failed to send OTP email to {email} (purpose={purpose})")
    return otp


def _verify_otp(email: str, otp: str, purpose: str) -> bool:
    record = repository.get_latest_otp(email, purpose)
    if not record:
        return False
    if record["attempts"] >= MAX_OTP_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

    expires_at = datetime.fromisoformat(record["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) >= expires_at:
        return False

    if not secrets.compare_digest(record["otp_hash"], _hash_otp(otp)):
        repository.increment_otp_attempts(record["id"], record["attempts"] + 1)
        return False

    repository.mark_otp_consumed(record["id"])
    return True


def _build_user_out(user_id: str, email: str) -> dict:
    profile = repository.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    org = repository.get_org_by_id(profile["organization_id"])
    auth_user = supabase_admin.auth.admin.get_user_by_id(user_id)
    full_name = (auth_user.user.user_metadata or {}).get("full_name", "") if auth_user and auth_user.user else ""
    return {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "organization_id": profile["organization_id"],
        "organization_name": org["name"] if org else "",
        "created_at": profile.get("created_at", ""),
    }


def signup(full_name: str, email: str, password: str, organization_name: str) -> str:
    existing = supabase_admin.auth.admin.list_users()
    match = next((u for u in existing if u.email == email), None)

    if match and match.email_confirmed_at:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    if match:
        # Unconfirmed account from a previous incomplete signup — resend OTP, don't recreate.
        _issue_otp(email, "signup")
        return email

    try:
        created = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": False,
            "user_metadata": {"full_name": full_name},
        })
    except Exception as e:
        logger.error(f"Signup create_user failed for {email}: {e}")
        raise HTTPException(status_code=400, detail="Could not create account. Please try again.")

    user_id = created.user.id
    org = repository.create_organization(organization_name)
    repository.create_user_profile(user_id, org["id"], email)
    _issue_otp(email, "signup")
    return email


def resend_signup_otp(email: str):
    _issue_otp(email, "signup")


def _post_auth(user_id: str, email: str):
    """Issues a real Supabase session (access + refresh token) for an already-
    verified user, via a generated magic link — avoids ever re-handling the
    user's plaintext password after signup verification."""
    link_res = supabase_admin.auth.admin.generate_link({
        "type": "magiclink",
        "email": email,
    })
    token_hash = link_res.properties.hashed_token
    verified = supabase_admin.auth.verify_otp({"token_hash": token_hash, "type": "magiclink"})
    user_out = _build_user_out(user_id, email)
    return user_out, verified.session.access_token, verified.session.refresh_token


def verify_signup_otp(email: str, otp: str):
    if not _verify_otp(email, otp, "signup"):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    users = supabase_admin.auth.admin.list_users()
    match = next((u for u in users if u.email == email), None)
    if not match:
        raise HTTPException(status_code=404, detail="Account not found")

    supabase_admin.auth.admin.update_user_by_id(match.id, {"email_confirm": True})
    return _post_auth(match.id, email)


def login(email: str, password: str):
    try:
        result = supabase_admin.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        logger.info(f"Login failed for {email}: {e}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not result.session:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_out = _build_user_out(result.user.id, email)
    return user_out, result.session.access_token, result.session.refresh_token


def forgot_password(email: str):
    users = supabase_admin.auth.admin.list_users()
    match = next((u for u in users if u.email == email), None)
    if match:
        _issue_otp(email, "password_reset")
    # Always returns silently regardless of whether the email exists —
    # caller (routes.py) returns the same generic message either way.


def reset_password(email: str, otp: str, new_password: str):
    if not _verify_otp(email, otp, "password_reset"):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    users = supabase_admin.auth.admin.list_users()
    match = next((u for u in users if u.email == email), None)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    supabase_admin.auth.admin.update_user_by_id(match.id, {"password": new_password})


def refresh_session(refresh_token: str):
    try:
        result = supabase_admin.auth.refresh_session(refresh_token)
    except Exception as e:
        logger.info(f"Refresh failed: {e}")
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    if not result.session:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    user_out = _build_user_out(result.user.id, result.user.email)
    return result.session.access_token, result.session.refresh_token, user_out
