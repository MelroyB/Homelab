from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, get_settings_dep, require_admin
from app.core.config import Settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse, RefreshResponse, UserOut
from app.services.audit.service import AuditService
from app.services.auth import (
    REFRESH_COOKIE_NAME,
    AuthError,
    authenticate,
    clear_auth_cookies,
    issue_tokens,
    revoke_refresh_token,
    rotate_refresh,
    set_auth_cookies,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> LoginResponse:
    audit = AuditService(db)
    try:
        user = authenticate(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        audit.record(
            actor_user_id=None,
            action="login",
            resource_type="auth",
            resource_id=payload.email,
            status="failed",
            ip_address=get_client_ip(request),
            metadata_json={"reason": str(exc)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    access, refresh, csrf = issue_tokens(db, settings, user=user)
    set_auth_cookies(
        response,
        settings,
        access_token=access,
        refresh_token=refresh,
        csrf_token=csrf,
    )

    audit.record(
        actor_user_id=user.id,
        action="login",
        resource_type="auth",
        resource_id=user.id,
        status="success",
        ip_address=get_client_ip(request),
    )
    db.commit()

    return LoginResponse(
        user=UserOut.model_validate(user),
        csrf_token=csrf,
        access_token_expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh_tokens(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
) -> RefreshResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )

    try:
        access, refresh, csrf = rotate_refresh(db, settings, refresh_token=refresh_token)
    except AuthError as exc:
        clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    set_auth_cookies(
        response,
        settings,
        access_token=access,
        refresh_token=refresh,
        csrf_token=csrf,
    )
    return RefreshResponse(
        csrf_token=csrf,
        access_token_expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    current_user: User = Depends(get_current_user),
) -> None:
    revoke_refresh_token(db, settings, refresh_token=request.cookies.get(REFRESH_COOKIE_NAME))
    clear_auth_cookies(response)

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action="logout",
        resource_type="auth",
        resource_id=current_user.id,
        status="success",
        ip_address=get_client_ip(request),
    )
    db.commit()


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=UserOut.model_validate(current_user))


@router.get("/users", response_model=list[UserOut])
def list_users(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    users = db.scalars(select(User).order_by(User.created_at.asc())).all()
    return [UserOut.model_validate(user) for user in users]
