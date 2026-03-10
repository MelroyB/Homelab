from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        actor_user_id: str | None,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str,
        ip_address: str | None,
        before: dict | None = None,
        after: dict | None = None,
        metadata_json: dict | None = None,
    ) -> None:
        event = AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            ip_address=ip_address,
            before=before or {},
            after=after or {},
            metadata_json=metadata_json or {},
        )
        self.db.add(event)
        self.db.flush()
