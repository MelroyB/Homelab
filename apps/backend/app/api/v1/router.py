from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit,
    auth,
    backups,
    bootstrap,
    dashboard,
    docker_manager,
    health,
    services,
    settings,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(bootstrap.router, prefix="/bootstrap", tags=["bootstrap"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(docker_manager.router, prefix="/docker", tags=["docker"])
api_router.include_router(backups.router, prefix="/backups", tags=["backups"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
