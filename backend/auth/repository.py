"""All Supabase access for the auth module lives here."""
from typing import Optional
from datetime import datetime, timezone
from config import supabase_admin


def get_org_by_id(org_id: str) -> Optional[dict]:
    result = supabase_admin.table("organizations").select("*").eq("id", org_id).execute()
    return result.data[0] if result.data else None


def create_organization(name: str) -> dict:
    result = supabase_admin.table("organizations").insert({"name": name}).execute()
    return result.data[0]


def get_user_profile(user_id: str) -> Optional[dict]:
    result = supabase_admin.table("user_profiles").select("*").eq("id", user_id).execute()
    return result.data[0] if result.data else None


def get_user_profile_by_email(email: str) -> Optional[dict]:
    result = supabase_admin.table("user_profiles").select("id,email").eq("email", email).limit(1).execute()
    return result.data[0] if result.data else None


def create_user_profile(user_id: str, organization_id: str, email: str) -> dict:
    result = supabase_admin.table("user_profiles").insert({
        "id": user_id, "organization_id": organization_id, "email": email
    }).execute()
    return result.data[0]


def delete_incomplete_signup(user_id: str, organization_id: str) -> None:
    supabase_admin.table("user_profiles").delete().eq("id", user_id).execute()
    supabase_admin.table("organizations").delete().eq("id", organization_id).execute()


def create_otp(email: str, otp_hash: str, purpose: str, expires_at: str) -> dict:
    result = supabase_admin.table("auth_otps").insert({
        "email": email, "otp_hash": otp_hash, "purpose": purpose, "expires_at": expires_at
    }).execute()
    return result.data[0]


def get_latest_otp(email: str, purpose: str) -> Optional[dict]:
    result = supabase_admin.table("auth_otps") \
        .select("*").eq("email", email).eq("purpose", purpose) \
        .is_("consumed_at", "null") \
        .order("created_at", desc=True).limit(1).execute()
    return result.data[0] if result.data else None


def mark_otp_consumed(otp_id: str) -> bool:
    res = supabase_admin.table("auth_otps") \
        .update({"consumed_at": datetime.now(timezone.utc).isoformat()}) \
        .eq("id", otp_id).is_("consumed_at", "null").execute()
    return bool(res.data)


def delete_otp(otp_id: str) -> None:
    supabase_admin.table("auth_otps").delete().eq("id", otp_id).execute()


def increment_otp_attempts(otp_id: str, attempts: int) -> bool:
    res = supabase_admin.table("auth_otps").update({"attempts": attempts}) \
        .eq("id", otp_id).eq("attempts", attempts - 1).execute()
    return bool(res.data)
