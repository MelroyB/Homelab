from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditEventResponse, AuditListResponse

router = APIRouter()


@router.get("", response_model=AuditListResponse)
def list_audit_events(
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
) -> AuditListResponse:
    events = db.scalars(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    ).all()
    return AuditListResponse(items=[AuditEventResponse.model_validate(event) for event in events])
