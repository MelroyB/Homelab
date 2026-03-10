from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_settings_dep, require_admin
from app.core.config import Settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.backup import (
    BackupCreateResponse,
    BackupListItem,
    BackupListResponse,
    BackupRestoreRequest,
)
from app.services.audit.service import AuditService
from app.services.backup.service import BackupService

router = APIRouter()


@router.post("/export", response_model=BackupCreateResponse, status_code=status.HTTP_201_CREATED)
def export_backup(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    current_user: User = Depends(require_admin),
) -> BackupCreateResponse:
    service = BackupService(db, settings)
    snapshot = service.create_snapshot(current_user)

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action="backup_export",
        resource_type="backup",
        resource_id=snapshot.id,
        status="success",
        ip_address=get_client_ip(request),
        metadata_json={"name": snapshot.name},
    )
    db.commit()

    return BackupCreateResponse(
        id=snapshot.id,
        name=snapshot.name,
        checksum=snapshot.checksum,
        created_at=snapshot.created_at,
    )


@router.get("", response_model=BackupListResponse)
def list_backups(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    _admin_user: User = Depends(require_admin),
) -> BackupListResponse:
    service = BackupService(db, settings)
    items = service.list_snapshots()
    return BackupListResponse(
        items=[
            BackupListItem(
                id=item.id,
                name=item.name,
                checksum=item.checksum,
                created_at=item.created_at,
                restored_at=item.restored_at,
            )
            for item in items
        ]
    )


@router.post("/restore", response_model=BackupCreateResponse)
def restore_backup(
    payload: BackupRestoreRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    current_user: User = Depends(require_admin),
) -> BackupCreateResponse:
    service = BackupService(db, settings)
    try:
        snapshot = service.restore_snapshot(snapshot_id=payload.snapshot_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action="backup_restore",
        resource_type="backup",
        resource_id=snapshot.id,
        status="success",
        ip_address=get_client_ip(request),
    )
    db.commit()

    return BackupCreateResponse(
        id=snapshot.id,
        name=snapshot.name,
        checksum=snapshot.checksum,
        created_at=snapshot.created_at,
    )
