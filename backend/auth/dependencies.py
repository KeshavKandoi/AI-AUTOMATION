"""Shared auth dependencies. Extracted from main.py so auth/routes.py can use
the same JWT verification without a circular import (main.py imports the
auth router). Behavior is unchanged from the original — same JWT decode,
same secret, same error handling."""
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from config import settings


def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_org_id(user: dict = Depends(get_current_user)) -> str:
    """Resolves the authenticated user's organization_id from their real
    user_profile — NEVER from a client-supplied org_id query param. This
    is the actual authorization boundary: routes using this dependency
    can only ever act on the organization the authenticated JWT's
    subject genuinely belongs to, regardless of what org_id a client
    might otherwise try to pass.

    Raises 404 (not 401) if the authenticated user has no organization
    mapping — this is a distinct failure mode from "not authenticated"
    and should not be confused with it."""
    from auth import repository

    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")

    profile = repository.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="No organization found for this user")

    return profile["organization_id"]
