from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.auth import AuthSession
from app.models.user import User

ACCESS_COOKIE_NAME = "hl_access"
REFRESH_COOKIE_NAME = "hl_refresh"
CSRF_COOKIE_NAME = "hl_csrf"


class AuthError(Exception):
    pass


def bootstrap_required(db: Session) -> bool:
    user_count = db.scalar(select(func.count()).select_from(User))
    return user_count == 0


def create_admin_user(db: Session, *, email: str, password: str) -> User:
    if not bootstrap_required(db):
        raise AuthError("Bootstrap already completed")
    user = User(email=email.lower(), hashed_password=hash_password(password), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active:
        raise AuthError("Invalid credentials")
    if not verify_password(password, user.hashed_password):
        raise AuthError("Invalid credentials")
    return user


def issue_tokens(db: Session, settings: Settings, *, user: User) -> tuple[str, str, str]:
    session = AuthSession(
        user_id=user.id,
        refresh_jti=uuid4().hex,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    access = create_access_token(settings, user_id=user.id, role=user.role)
    refresh = create_refresh_token(
        settings,
        user_id=user.id,
        role=user.role,
        session_id=session.id,
        refresh_jti=session.refresh_jti,
    )
    csrf = secrets.token_urlsafe(24)
    return access, refresh, csrf


def rotate_refresh(db: Session, settings: Settings, *, refresh_token: str) -> tuple[str, str, str]:
    try:
        payload = decode_token(settings, refresh_token, token_type="refresh")
    except TokenError as exc:
        raise AuthError("Invalid refresh token") from exc

    session_id = payload.get("sid")
    jti = payload.get("jti")
    user_id = payload.get("sub")
    role = payload.get("role", "admin")

    if not session_id or not jti or not user_id:
        raise AuthError("Invalid refresh token payload")

    session = db.scalar(select(AuthSession).where(AuthSession.id == session_id))
    if session is None or session.revoked_at is not None:
        raise AuthError("Session revoked")
    if session.refresh_jti != jti:
        raise AuthError("Refresh token rotation mismatch")
    if session.expires_at < datetime.now(timezone.utc):
        raise AuthError("Refresh token expired")

    session.refresh_jti = uuid4().hex
    db.add(session)
    db.commit()

    access = create_access_token(settings, user_id=user_id, role=role)
    refresh = create_refresh_token(
        settings,
        user_id=user_id,
        role=role,
        session_id=session_id,
        refresh_jti=session.refresh_jti,
    )
    csrf = secrets.token_urlsafe(24)
    return access, refresh, csrf


def revoke_refresh_token(db: Session, settings: Settings, *, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    try:
        payload = decode_token(settings, refresh_token, token_type="refresh")
    except TokenError:
        return

    sid = payload.get("sid")
    if not sid:
        return

    session = db.scalar(select(AuthSession).where(AuthSession.id == sid))
    if session is None:
        return

    session.revoked_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()


def set_auth_cookies(
    response: Response,
    settings: Settings,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.csrf_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")
