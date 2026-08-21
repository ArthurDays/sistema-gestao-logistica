import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.core.config import settings


def hash_password(password: str, salt: str | None = None) -> str:
    encoded_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), encoded_salt.encode(), 600_000)
    return f"pbkdf2_sha256$600000${encoded_salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, rounds, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256" or rounds != "600000":
            return False
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), password_hash)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(subject: str, organization_id: str, role: str) -> str:
    now = datetime.now(UTC)
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    claims = {
        "sub": subject,
        "organization_id": organization_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    }
    payload = _b64(json.dumps(claims, separators=(",", ":")).encode())
    signature = _b64(
        hmac.new(settings.jwt_secret_key.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{signature}"


def decode_access_token(token: str) -> dict[str, object]:
    try:
        header, payload, signature = token.split(".")
        signature_input = f"{header}.{payload}".encode()
        expected_digest = hmac.new(settings.jwt_secret_key.encode(), signature_input, hashlib.sha256).digest()
        expected = _b64(expected_digest)
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        claims = json.loads(_unb64(payload))
        if not isinstance(claims, dict) or int(claims["exp"]) <= int(datetime.now(UTC).timestamp()):
            raise ValueError("expired token")
        return claims
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        ) from None


def create_oauth_state() -> str:
    now = datetime.now(UTC)
    claims = {
        "nonce": secrets.token_urlsafe(24),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
    }
    payload = _b64(json.dumps(claims, separators=(",", ":")).encode())
    signature = _b64(hmac.new(settings.jwt_secret_key.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def verify_oauth_state(value: str) -> None:
    try:
        payload, signature = value.split(".")
        expected = _b64(hmac.new(settings.jwt_secret_key.encode(), payload.encode(), hashlib.sha256).digest())
        claims = json.loads(_unb64(payload))
        expired = int(claims["exp"]) <= int(datetime.now(UTC).timestamp())
        if not hmac.compare_digest(signature, expected) or expired:
            raise ValueError("invalid state")
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Estado OAuth inválido",
        ) from None
