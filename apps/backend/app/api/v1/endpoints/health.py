from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_docker_gateway, get_settings_dep
from app.core.config import Settings
from app.db.session import get_db
from app.schemas.health import ReadinessResponse
from app.services.docker_gateway import DockerGateway
from app.services.health.service import ReadinessService

router = APIRouter()


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/ready", response_model=ReadinessResponse)
def ready(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> ReadinessResponse:
    return ReadinessService(db, settings, docker_gateway).check()
