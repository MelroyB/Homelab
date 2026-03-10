from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_docker_gateway, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardOverviewResponse
from app.services.docker_gateway import DockerGateway
from app.services.service_state import ServiceStateService

router = APIRouter()


@router.get("/overview", response_model=DashboardOverviewResponse)
def overview(
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> DashboardOverviewResponse:
    service_state = ServiceStateService(db, docker_gateway)
    services = service_state.list_states()
    healthy_count = sum(
        1 for item in services if item.health in {"healthy", "unknown"} and item.state == "running"
    )
    degraded_count = len(services) - healthy_count
    return DashboardOverviewResponse(
        generated_at=datetime.now(timezone.utc),
        service_count=len(services),
        healthy_service_count=healthy_count,
        degraded_service_count=degraded_count,
        services=services,
    )
