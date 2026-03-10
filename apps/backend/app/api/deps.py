from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import TokenError, decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth import ACCESS_COOKIE_NAME
from app.services.docker_gateway import DockerGateway

settings_singleton = get_settings()
docker_gateway_singleton = DockerGateway(settings_singleton)


def get_settings_dep() -> Settings:
    return settings_singleton


def get_docker_gateway() -> DockerGateway:
    return docker_gateway_singleton


def get_client_ip(request: Request) -> str | None:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def get_current_user(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    access_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE_NAME)] = None,
) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(settings, access_token, token_type="access")
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
        )

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user
