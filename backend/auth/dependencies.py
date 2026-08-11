"""
Shared auth dependencies.

get_current_user verifies Supabase-issued JWTs. This project uses
Supabase's asymmetric (ES256) JWT signing keys — the default for all
projects created after Oct 1, 2025 (confirmed via Supabase's own JWKS
endpoint and official docs) — so tokens are verified against the
project's public keys (JWKS), not a static shared secret. HS256 is kept
as a fallback for compatibility with any legacy token/environment still
using the shared secret, per Supabase's own documented dual-support
pattern during migration.

JWKS keys are fetched once and cached in memory; a cache miss on `kid`
(e.g. after key rotation) triggers exactly one re-fetch before failing,
matching Supabase's documented rotation model.
"""
from fastapi import Depends, HTTPException, Header
from jose import jwt, jwk, JWTError
import httpx

from config import settings

_jwks_cache: dict = {}


def _fetch_jwks() -> dict:
    global _jwks_cache
    url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    _jwks_cache = {key["kid"]: key for key in data.get("keys", [])}
    return _jwks_cache


def _get_signing_key(kid: str):
    if kid not in _jwks_cache:
        _fetch_jwks()
    key_data = _jwks_cache.get(kid)
    if not key_data:
        raise JWTError(f"No matching key found for kid={kid}")
    return jwk.construct(key_data)


def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ")[1]

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    alg = unverified_header.get("alg")

    try:
        if alg == "ES256":
            kid = unverified_header.get("kid")
            if not kid:
                raise JWTError("Token missing kid header")
            signing_key = _get_signing_key(kid)
            payload = jwt.decode(
                token, signing_key.to_pem().decode() if hasattr(signing_key, "to_pem") else signing_key,
                algorithms=["ES256"], audience="authenticated",
            )
        else:
            payload = jwt.decode(
                token, settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"], audience="authenticated",
            )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception:
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
