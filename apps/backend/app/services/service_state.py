from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.service import ManagedService, ServiceConfigVersion
from app.schemas.service import ServiceState
from app.services.docker_gateway import DockerGateway


class ServiceStateService:
    def __init__(self, db: Session, docker_gateway: DockerGateway) -> None:
        self.db = db
        self.docker_gateway = docker_gateway

    def list_states(self) -> list[ServiceState]:
        services = self.db.scalars(
            select(ManagedService).order_by(ManagedService.category, ManagedService.slug)
        ).all()
        return [self._state_for_service(service) for service in services]

    def _state_for_service(self, service: ManagedService) -> ServiceState:
        inspect_data = self.docker_gateway.inspect(service.container_name)
        latest = self.db.scalar(
            select(ServiceConfigVersion)
            .where(ServiceConfigVersion.service_slug == service.slug)
            .order_by(ServiceConfigVersion.version.desc())
            .limit(1)
        )
        last_change: datetime | None = latest.created_at if latest else None

        return ServiceState(
            slug=service.slug,
            name=service.name,
            category=service.category,
            container_name=service.container_name,
            enabled=service.enabled,
            state=str(inspect_data.get("state", "unknown")),
            health=str(inspect_data.get("health", "unknown")),
            uptime_seconds=inspect_data.get("uptime_seconds"),
            ports=inspect_data.get("ports", []),
            config_validation_status=latest.validation_status if latest else None,
            last_config_change=last_change,
            last_config_version=latest.version if latest else None,
        )
