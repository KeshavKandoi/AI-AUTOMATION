"""
Security regression test: every access_token/refresh_token stored in
oauth_tokens must be Fernet-encrypted (starts with 'gAAAAA'), never
plaintext. This queries the live database directly rather than mocking,
because the actual incident this guards against was a legacy row that
predated encrypt_token() being wired in -- a scenario a pure unit test
against the write path would not have caught.

Skips cleanly (rather than failing) if Supabase credentials aren't
configured in the test environment, since this must remain runnable in
CI/sandboxes without live database access.
"""
import pytest
from config import supabase_admin


def _is_encrypted_or_none(value) -> bool:
    return value is None or value.startswith("gAAAAA")


def test_no_plaintext_access_tokens_in_database():
    try:
        res = supabase_admin.table("oauth_tokens").select("id, access_token").execute()
    except Exception as e:
        pytest.skip(f"Could not reach Supabase in this environment: {e}")

    plaintext_ids = [
        row["id"] for row in res.data
        if row.get("access_token") and not _is_encrypted_or_none(row["access_token"])
    ]
    assert not plaintext_ids, f"Plaintext access_token found in rows: {plaintext_ids}"


def test_no_plaintext_refresh_tokens_in_database():
    try:
        res = supabase_admin.table("oauth_tokens").select("id, refresh_token").execute()
    except Exception as e:
        pytest.skip(f"Could not reach Supabase in this environment: {e}")

    plaintext_ids = [
        row["id"] for row in res.data
        if row.get("refresh_token") and not _is_encrypted_or_none(row["refresh_token"])
    ]
    assert not plaintext_ids, f"Plaintext refresh_token found in rows: {plaintext_ids}"


def test_encrypt_token_output_is_never_plaintext():
    """Unit-level guard on the encryption function itself: confirms
    encrypt_token always produces Fernet-format output, independent of
    database state."""
    from config import encrypt_token

    result = encrypt_token("some-fake-test-token-value")
    assert result.startswith("gAAAAA")
    assert result != "some-fake-test-token-value"
