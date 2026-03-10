from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BackupSnapshot(Base, TimestampMixin):
    __tablename__ = "backup_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), unique=True)
    file_path: Mapped[str] = mapped_column(String(512))
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    restored_at: Mapped[datetime] = mapped_column(nullable=True)
