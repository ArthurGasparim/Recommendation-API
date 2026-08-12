import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass


PBKDF2_ITERATIONS = 600_000
TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "43200"))


def _load_auth_secret() -> bytes:
    configured = os.getenv("AUTH_SECRET")
    if configured and len(configured) >= 32:
        return configured.encode("utf-8")
    if os.getenv("APP_ENV", "development").lower() == "production":
        raise RuntimeError("AUTH_SECRET deve possuir pelo menos 32 caracteres em produção")
    # Em desenvolvimento, uma chave efêmera evita segredo padrão versionado.
    return secrets.token_bytes(32)


AUTH_SECRET = _load_auth_secret()


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    is_admin: bool
    expires_at: int


class InvalidTokenError(ValueError):
    pass


def _encode_base64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    password_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), password_salt, PBKDF2_ITERATIONS
    )
    return _encode_base64(password_salt), _encode_base64(digest)


def verify_password(password: str, encoded_salt: str, expected_hash: str) -> bool:
    try:
        salt = _decode_base64(encoded_salt)
    except (ValueError, TypeError):
        return False
    _, candidate_hash = hash_password(password, salt)
    return hmac.compare_digest(candidate_hash, expected_hash)


def create_access_token(user_id: int, is_admin: bool) -> str:
    payload = {
        "sub": int(user_id),
        "admin": bool(is_admin),
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    body = _encode_base64(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = _encode_base64(
        hmac.new(AUTH_SECRET, body.encode("ascii"), hashlib.sha256).digest()
    )
    return f"{body}.{signature}"


def decode_access_token(token: str) -> TokenPayload:
    try:
        body, provided_signature = token.split(".", maxsplit=1)
        expected_signature = _encode_base64(
            hmac.new(AUTH_SECRET, body.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(provided_signature, expected_signature):
            raise InvalidTokenError("Assinatura inválida")
        payload = json.loads(_decode_base64(body))
        user_id = int(payload["sub"])
        expires_at = int(payload["exp"])
        is_admin = bool(payload.get("admin", False))
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        if isinstance(exc, InvalidTokenError):
            raise
        raise InvalidTokenError("Token inválido") from exc
    if expires_at <= int(time.time()):
        raise InvalidTokenError("Token expirado")
    return TokenPayload(
        user_id=user_id, is_admin=is_admin, expires_at=expires_at
    )

