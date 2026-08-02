from config import supabase_admin, logger


def log_action(organization_id: str, action: str, details: dict = None):
    try:
        supabase_admin.table("audit_logs").insert({
            "organization_id": organization_id,
            "action": action,
            "details": details or {}
        }).execute()
    except Exception as e:
        logger.error(f"Failed to write audit log ({action}): {e}")
