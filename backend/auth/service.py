import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from supabase_auth.errors import AuthApiError, AuthInvalidCredentialsError, AuthWeakPasswordError

from config import settings, get_auth_client, logger
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
    record = repository.create_otp(email, _hash_otp(otp), purpose, expires_at)
    try:
        sent = send_otp_email(email, otp, purpose)
    except Exception:
        sent = False
    if not sent:
        try:
            repository.mark_otp_consumed(record["id"])
        except Exception:
            repository.delete_otp(record["id"])
        logger.error(f"Failed to send OTP email (purpose={purpose})")
        raise HTTPException(status_code=502, detail="Could not send verification code. Please try again.")
    return otp


def _issue_otp_quiet(email: str, purpose: str) -> None:
    try:
        _issue_otp(email, purpose)
    except HTTPException as e:
        if e.status_code != 429:
            raise


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
        current = record
        for _ in range(3):
            if repository.increment_otp_attempts(current["id"], current["attempts"] + 1):
                break
            current = repository.get_latest_otp(email, purpose)
            if not current:
                break
        return False

    if not repository.mark_otp_consumed(record["id"]):
        return False
    return True


def _build_user_out(user_id: str, email: str, full_name: str = "") -> dict:
    """full_name is passed in from whatever Supabase Auth call already has it
    on hand (sign_in_with_password, verify_otp, refresh_session all return
    user_metadata directly) — avoids a second, separate Admin API call per
    request, which has shown itself to be intermittently unreliable."""
    profile = repository.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="This account never finished setup. Please sign up again.")
    org = repository.get_org_by_id(profile["organization_id"])
    return {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "organization_id": profile["organization_id"],
        "organization_name": org["name"] if org else "",
        "created_at": profile.get("created_at", ""),
    }


def signup(full_name: str, email: str, password: str, organization_name: str) -> str:
    auth_client = get_auth_client()

    try:
        match = repository.get_user_profile_by_email(email)
    except Exception:
        logger.exception("Signup: profile lookup failed")
        raise HTTPException(status_code=502, detail="Authentication service is temporarily unavailable. Please try again shortly.")

    if match:
        user = auth_client.auth.admin.get_user_by_id(match["id"]).user
        if not user.email_confirmed_at:
            _issue_otp_quiet(email, "signup")
        return email

    try:
        created = auth_client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": False,
            "user_metadata": {"full_name": full_name},
        })
    except Exception:
        logger.exception(f"Signup: create_user failed for {email}")
        raise HTTPException(status_code=400, detail="Could not create your account. Please check your details and try again.")

    user_id = created.user.id

    # From here on, a failure leaves an orphaned Supabase Auth user with no
    # org/profile — roll it back so signup can be cleanly retried.
    org = None
    try:
        org = repository.create_organization(organization_name)
        repository.create_user_profile(user_id, org["id"], email)
        _issue_otp(email, "signup")
    except Exception as error:
        logger.exception(f"Signup: post-user-creation step failed for {email} (user_id={user_id}) — rolling back")
        if org:
            try:
                repository.delete_incomplete_signup(user_id, org["id"])
            except Exception:
                logger.exception("Signup rollback: failed to remove incomplete profile and organization")
        try:
            auth_client.auth.admin.delete_user(user_id)
        except Exception:
            logger.exception(f"Signup rollback: failed to delete orphaned auth user {user_id} for {email} — MANUAL CLEANUP NEEDED")
        if isinstance(error, HTTPException) and error.status_code == 502:
            raise error
        raise HTTPException(status_code=500, detail="Could not complete signup. Please try again.")

    return email


def resend_signup_otp(email: str):
    try:
        profile = repository.get_user_profile_by_email(email)
        match = get_auth_client().auth.admin.get_user_by_id(profile["id"]).user if profile else None
    except Exception:
        return
    if match and not match.email_confirmed_at:
        _issue_otp_quiet(email, "signup")


def _post_auth(user_id: str, email: str, full_name: str = ""):
    """Issues a real Supabase session (access + refresh token) for an already-
    verified user, via a generated magic link — avoids ever re-handling the
    user's plaintext password after signup verification."""
    auth_client = get_auth_client()
    link_res = auth_client.auth.admin.generate_link({
        "type": "magiclink",
        "email": email,
    })
    token_hash = link_res.properties.hashed_token
    verified = auth_client.auth.verify_otp({"token_hash": token_hash, "type": "magiclink"})
    user_out = _build_user_out(user_id, email, full_name)
    return user_out, verified.session.access_token, verified.session.refresh_token


def verify_signup_otp(email: str, otp: str):
    if not _verify_otp(email, otp, "signup"):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    auth_client = get_auth_client()
    profile = repository.get_user_profile_by_email(email)
    match = auth_client.auth.admin.get_user_by_id(profile["id"]).user if profile else None
    if not match:
        raise HTTPException(status_code=404, detail="Account not found")

    auth_client.auth.admin.update_user_by_id(match.id, {"email_confirm": True})
    full_name = (match.user_metadata or {}).get("full_name", "")
    return _post_auth(match.id, email, full_name)


def login(email: str, password: str):
    auth_client = get_auth_client()
    try:
        result = auth_client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        logger.exception(f"Login failed for {email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not result.session:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    full_name = (result.user.user_metadata or {}).get("full_name", "") if result.user else ""
    user_out = _build_user_out(result.user.id, email, full_name)
    return user_out, result.session.access_token, result.session.refresh_token


def forgot_password(email: str):
    try:
        profile = repository.get_user_profile_by_email(email)
    except Exception:
        # Don't leak whether the lookup itself failed vs the email not
        # existing — fail closed (no OTP sent) but still return the same
        # generic message so behavior is indistinguishable to the caller.
        return
    if profile:
        _issue_otp_quiet(email, "password_reset")
    # Always returns silently regardless of whether the email exists —
    # caller (routes.py) returns the same generic message either way.


def reset_password(email: str, otp: str, new_password: str):
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if not _verify_otp(email, otp, "password_reset"):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    profile = repository.get_user_profile_by_email(email)
    if not profile:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    _update_and_confirm_password(profile["id"], email, new_password)


def _update_and_confirm_password(user_id: str, email: str, new_password: str) -> None:
    try:
        get_auth_client().auth.admin.update_user_by_id(user_id, {"password": new_password})
    except AuthWeakPasswordError:
        raise HTTPException(status_code=400, detail="New password does not meet the account password policy") from None
    except Exception as exc:
        logger.error("Password update failed for user_id=%s (%s)", user_id, type(exc).__name__)
        raise HTTPException(status_code=502, detail="Could not update password. Please try again.") from None

    try:
        result = get_auth_client().auth.sign_in_with_password({"email": email, "password": new_password})
        if not result.user or result.user.id != user_id:
            raise ValueError("Password verification returned the wrong account")
    except Exception as exc:
        logger.error("Password verification failed for user_id=%s (%s)", user_id, type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="Password update may have succeeded, but verification failed. Try signing in with the new password.",
        ) from None


def change_password(user_id: str, email: str, current_password: str, new_password: str):
    """Verifies the current password by attempting a real sign-in (proves the
    caller actually knows it, not just that they hold a valid access token —
    e.g. protects against a stolen/leaked token being used to lock the real
    owner out), then updates via the Admin API. Does not touch or invalidate
    the caller's existing session."""
    if not user_id or not email:
        raise HTTPException(status_code=401, detail="Session is incomplete. Please sign in again.")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    auth_client = get_auth_client()
    try:
        result = auth_client.auth.sign_in_with_password({"email": email, "password": current_password})
    except AuthInvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Current password is incorrect") from None
    except AuthApiError as exc:
        if str(getattr(exc, "code", "")) == "invalid_credentials":
            raise HTTPException(status_code=401, detail="Current password is incorrect") from None
        raise HTTPException(status_code=502, detail="Authentication service is unavailable. Please try again.") from None
    except Exception:
        raise HTTPException(status_code=502, detail="Authentication service is unavailable. Please try again.") from None
    if not result.user or result.user.id != user_id:
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    _update_and_confirm_password(user_id, email, new_password)


def refresh_session(refresh_token: str):
    auth_client = get_auth_client()
    try:
        result = auth_client.auth.refresh_session(refresh_token)
    except Exception:
        logger.exception("Refresh failed")
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    if not result.session:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    full_name = (result.user.user_metadata or {}).get("full_name", "") if result.user else ""
    user_out = _build_user_out(result.user.id, result.user.email, full_name)
    return result.session.access_token, result.session.refresh_token, user_out
