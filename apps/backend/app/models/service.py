from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ManagedService(Base, TimestampMixin):
    __tablename__ = "managed_services"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(64), default="core")
    container_name: Mapped[str] = mapped_column(String(128), unique=True)
    config_path: Mapped[str] = mapped_column(String(255), default="")
    supports_reload: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_raw_edit: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ServiceConfigVersion(Base):
    __tablename__ = "service_config_versions"
    __table_args__ = (UniqueConstraint("service_slug", "version", name="uq_service_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    service_slug: Mapped[str] = mapped_column(
        String(64), ForeignKey("managed_services.slug", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_config: Mapped[str] = mapped_column(Text, default="")
    rendered_config: Mapped[str] = mapped_column(Text, default="")
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    validation_status: Mapped[str] = mapped_column(String(32), default="pending")
    validation_errors: Mapped[list] = mapped_column(JSON, default=list)
    apply_status: Mapped[str] = mapped_column(String(32), default="pending")
    apply_message: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    applied_at: Mapped[datetime] = mapped_column(nullable=True)
