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
