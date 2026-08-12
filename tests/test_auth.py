import pytest

from auth import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_salted_and_verifiable():
    first_salt, first_hash = hash_password("password123")
    second_salt, second_hash = hash_password("password123")

    assert first_salt != second_salt
    assert first_hash != second_hash
    assert verify_password("password123", first_salt, first_hash)
    assert not verify_password("incorrect", first_salt, first_hash)


def test_signed_token_rejects_tampering():
    token = create_access_token(user_id=42, is_admin=False)
    payload = decode_access_token(token)

    assert payload.user_id == 42
    assert payload.is_admin is False

    body, signature = token.split(".")
    replacement = "A" if signature[-1] != "A" else "B"
    tampered = f"{body}.{signature[:-1]}{replacement}"
    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)
