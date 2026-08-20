from fastapi import APIRouter, Depends
from auth.dependencies import get_current_user
from account import service
from account.schemas import DeleteAccountRequest

router = APIRouter(prefix="/account", tags=["account"])


@router.post("/delete")
def delete_account(payload: DeleteAccountRequest, user: dict = Depends(get_current_user)):
    service.delete_account(user.get("sub"), user.get("email"), payload.password)
    return {"message": "Account deleted"}
