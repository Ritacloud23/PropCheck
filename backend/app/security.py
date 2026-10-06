import base64
import hashlib
import hmac
import time
from datetime import timedelta

import jwt
from pwdlib import PasswordHash

from app.config import settings
from app.models.base import utcnow

_hasher = PasswordHash.recommended()  # Argon2id


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(user_id: int, role: str) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


# ---------- Signed URLs for private files ----------


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def sign_file_key(key: str, ttl_seconds: int | None = None) -> str:
    expires = int(time.time()) + (ttl_seconds or settings.signed_url_ttl_seconds)
    body = f"{key}|{expires}".encode()
    sig = hmac.new(settings.file_signing_secret.encode(), body, hashlib.sha256).digest()
    return f"{_b64(body)}.{_b64(sig)}"


def verify_file_token(token: str) -> str | None:
    """Return the storage key if the token is authentic and unexpired."""
    try:
        body_b64, sig_b64 = token.split(".", 1)
        body = _unb64(body_b64)
        expected = hmac.new(settings.file_signing_secret.encode(), body, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(sig_b64)):
            return None
        key, expires = body.decode().rsplit("|", 1)
        if int(expires) < int(time.time()):
            return None
        return key
    except Exception:
        return None
