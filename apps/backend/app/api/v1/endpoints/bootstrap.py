from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip
from app.db.session import get_db
from app.schemas.auth import BootstrapAdminRequest, BootstrapStatusResponse, UserOut
from app.services.audit.service import AuditService
from app.services.auth import AuthError, bootstrap_required, create_admin_user

router = APIRouter()


@router.get("/status", response_model=BootstrapStatusResponse)
def bootstrap_status(db: Session = Depends(get_db)) -> BootstrapStatusResponse:
    return BootstrapStatusResponse(bootstrap_required=bootstrap_required(db))


@router.post("/admin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(
    payload: BootstrapAdminRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> UserOut:
    audit = AuditService(db)
    try:
        user = create_admin_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        audit.record(
            actor_user_id=None,
            action="bootstrap_admin",
            resource_type="user",
            resource_id=payload.email,
            status="failed",
            ip_address=get_client_ip(request),
            metadata_json={"reason": str(exc)},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    audit.record(
        actor_user_id=user.id,
        action="bootstrap_admin",
        resource_type="user",
        resource_id=user.id,
        status="success",
        ip_address=get_client_ip(request),
        after={"email": user.email, "role": user.role},
    )
    db.commit()
    return UserOut.model_validate(user)
