import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from passlib.hash import argon2
from jose import JWTError, jwt
from app.core.config import settings


def hash_password(password: str) -> str:
    return argon2.using(type="ID").hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return argon2.verify(password, password_hash)
    except Exception:
        return False


def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain a lowercase letter")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain an uppercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain a number")
    if not any(c in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~" for c in password):
        raise ValueError("Password must contain a special character")


def create_access_token(subject: str, session_id: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": subject,
        "type": "access",
        "jti": secrets.token_hex(16),
        "session_id": session_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise
    return payload


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def create_random_token() -> str:
    return secrets.token_urlsafe(48)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_expiration(minutes: int | None = None, hours: int | None = None, days: int | None = None, seconds: int | None = None) -> datetime:
    delta = timedelta(minutes=minutes or 0, hours=hours or 0, days=days or 0, seconds=seconds or 0)
    return now_utc() + delta


def create_sso_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=settings.SSO_COOKIE_EXPIRE_DAYS))
    payload = {
        "sub": user_id,
        "type": "sso",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_sso_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise
    return payload
