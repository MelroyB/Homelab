from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.service import ManagedService
from app.services.registry import SERVICE_CATALOG


def seed_services(db: Session) -> None:
    for service_meta in SERVICE_CATALOG:
        existing = db.scalar(select(ManagedService).where(ManagedService.slug == service_meta.slug))
        if existing:
            existing.name = service_meta.name
            existing.description = service_meta.description
            existing.category = service_meta.category
            existing.container_name = service_meta.container_name
            existing.config_path = service_meta.config_path
            existing.supports_reload = service_meta.supports_reload
            existing.supports_raw_edit = service_meta.supports_raw_edit
            db.add(existing)
            continue
        db.add(
            ManagedService(
                slug=service_meta.slug,
                name=service_meta.name,
                description=service_meta.description,
                category=service_meta.category,
                container_name=service_meta.container_name,
                config_path=service_meta.config_path,
                supports_reload=service_meta.supports_reload,
                supports_raw_edit=service_meta.supports_raw_edit,
            )
        )
    db.commit()
