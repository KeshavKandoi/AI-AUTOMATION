from fastapi import APIRouter, Response, Request, HTTPException, Depends
from config import settings
from auth import service
from auth.dependencies import get_current_user
from auth.schemas import (
    SignupRequest, LoginRequest, VerifyOtpRequest, ResendOtpRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Frontend (localhost:5173 in dev, or the deployed frontend origin in prod)
# and backend (Render) are cross-site in every environment this app runs in
# — SameSite=Lax would be silently dropped by the browser on cross-site
# fetch/XHR calls (only Strict/Lax-exempt top-level navigations get Lax
# cookies), breaking the refresh-cookie flow specifically in local dev
# testing. SameSite=None is required unconditionally here, not just in prod.
COOKIE_KWARGS = dict(
    key="refresh_token",
    httponly=True,
    secure=True,
    samesite="none",
    path="/auth",
)
if settings.COOKIE_DOMAIN:
    COOKIE_KWARGS["domain"] = settings.COOKIE_DOMAIN


def _set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(value=refresh_token, max_age=60 * 60 * 24 * 30, **COOKIE_KWARGS)


def _clear_refresh_cookie(response: Response):
    clear_kwargs = {k: v for k, v in COOKIE_KWARGS.items() if k != "key"}
    response.delete_cookie(key="refresh_token", **{k: v for k, v in clear_kwargs.items() if k in ("path", "domain")})


@router.post("/signup")
def signup(payload: SignupRequest):
    email = service.signup(payload.full_name, payload.email, payload.password, payload.organization_name)
    return {"message": "Verification code sent", "email": email}


@router.post("/resend-otp")
def resend_otp(payload: ResendOtpRequest):
    service.resend_signup_otp(payload.email)
    return {"message": "Verification code sent"}


@router.post("/verify-otp")
def verify_otp(payload: VerifyOtpRequest, response: Response):
    user, access_token, refresh_token = service.verify_signup_otp(payload.email, payload.otp)
    _set_refresh_cookie(response, refresh_token)
    return {"user": user, "access_token": access_token}


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    user, access_token, refresh_token = service.login(payload.email, payload.password)
    _set_refresh_cookie(response, refresh_token)
    return {"user": user, "access_token": access_token}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    service.forgot_password(payload.email)
    return {"message": "If an account exists with this email, a reset code has been sent."}


@router.post("/resend-reset-otp")
def resend_reset_otp(payload: ForgotPasswordRequest):
    service.forgot_password(payload.email)
    return {"message": "If an account exists with this email, a new code has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    service.reset_password(payload.email, payload.otp, payload.new_password)
    return {"message": "Password reset successfully"}


@router.post("/refresh")
def refresh(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No session found")
    access_token, new_refresh_token, user = service.refresh_session(refresh_token)
    _set_refresh_cookie(response, new_refresh_token)
    return {"user": user, "access_token": access_token}


@router.post("/logout")
def logout(response: Response):
    _clear_refresh_cookie(response)
    return {"message": "Logged out"}


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    service.change_password(user.get("sub"), user.get("email"), payload.current_password, payload.new_password)
    return {"message": "Password changed successfully"}
