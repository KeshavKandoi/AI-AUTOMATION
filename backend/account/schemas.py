from pydantic import BaseModel


class DeleteAccountRequest(BaseModel):
    # Requires re-entering the password as a final confirmation step for an
    # irreversible action — same defense-in-depth pattern as GitHub/most
    # SaaS apps use for account deletion.
    password: str
