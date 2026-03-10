from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from app.core.config import Settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ALGORITHM = "HS256"


class TokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


def create_access_token(settings: Settings, *, user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iat": now,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    settings: Settings,
    *,
    user_id: str,
    role: str,
    session_id: str,
    refresh_jti: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "sid": session_id,
        "jti": refresh_jti,
        "type": "refresh",
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
        "iat": now,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(settings: Settings, token: str, *, token_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid token") from exc
    if payload.get("type") != token_type:
        raise TokenError("Unexpected token type")
    return payload
