from fastapi import APIRouter, Depends, HTTPException
from auth.dependencies import get_current_user
from account import service
from account.schemas import DeleteAccountRequest
from config import logger

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/delete")
def delete_account(payload: DeleteAccountRequest, user: dict = Depends(get_current_user)):
    try:
        service.delete_account(user.get("sub"), user.get("email"), payload.password)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected account deletion failure for user_id=%s", user.get("sub"))
        raise HTTPException(status_code=500, detail="Account deletion failed unexpectedly. Please contact support before retrying.") from None
    return {"message": "Account deleted"}
