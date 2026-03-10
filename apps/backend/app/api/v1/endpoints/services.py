from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_docker_gateway, require_admin
from app.db.session import get_db
from app.models.service import ManagedService, ServiceConfigVersion
from app.models.user import User
from app.schemas.service import (
    ConfigApplyRequest,
    ConfigApplyResponse,
    ConfigValidateRequest,
    ConfigValidateResponse,
    ConfigVersionResponse,
    ServiceActionRequest,
    ServiceActionResponse,
    ServiceDetailResponse,
    ServiceState,
)
from app.services.adapters.implementations import build_adapter
from app.services.audit.service import AuditService
from app.services.config.manager import ConfigManager
from app.services.docker_gateway import DockerGateway
from app.services.service_state import ServiceStateService

router = APIRouter()


def _service_or_404(db: Session, slug: str) -> ManagedService:
    service = db.scalar(select(ManagedService).where(ManagedService.slug == slug))
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.get("", response_model=list[ServiceState])
def list_services(
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> list[ServiceState]:
    return ServiceStateService(db, docker_gateway).list_states()


@router.get("/{slug}", response_model=ServiceDetailResponse)
def service_detail(
    slug: str,
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> ServiceDetailResponse:
    service = _service_or_404(db, slug)
    state = ServiceStateService(db, docker_gateway)._state_for_service(service)
    active = db.scalar(
        select(ServiceConfigVersion).where(
            ServiceConfigVersion.service_slug == slug,
            ServiceConfigVersion.is_active.is_(True),
        )
    )
    return ServiceDetailResponse(
        service=state,
        active_config=ConfigVersionResponse.model_validate(active) if active else None,
    )


@router.post("/{slug}/actions", response_model=ServiceActionResponse)
def service_action(
    slug: str,
    payload: ServiceActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> ServiceActionResponse:
    service = _service_or_404(db, slug)
    if payload.action == "reload" and not service.supports_reload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reload not supported")

    adapter = build_adapter(service, docker_gateway)
    ok, message = adapter.controller.execute(service, payload.action)

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action=f"service_{payload.action}",
        resource_type="service",
        resource_id=service.slug,
        status="success" if ok else "failed",
        ip_address=get_client_ip(request),
        metadata_json={"message": message},
    )
    db.commit()

    return ServiceActionResponse(
        slug=slug,
        action=payload.action,
        status="success" if ok else "failed",
        message=message,
    )


@router.get("/{slug}/configs", response_model=list[ConfigVersionResponse])
def list_config_versions(
    slug: str,
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
) -> list[ConfigVersionResponse]:
    _service_or_404(db, slug)
    versions = db.scalars(
        select(ServiceConfigVersion)
        .where(ServiceConfigVersion.service_slug == slug)
        .order_by(ServiceConfigVersion.version.desc())
    ).all()
    return [ConfigVersionResponse.model_validate(version) for version in versions]


@router.post("/{slug}/configs/validate", response_model=ConfigValidateResponse)
def validate_config(
    slug: str,
    payload: ConfigValidateRequest,
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> ConfigValidateResponse:
    service = _service_or_404(db, slug)
    manager = ConfigManager(db, docker_gateway)
    valid, errors, rendered = manager.validate_candidate(
        service=service,
        config_json=payload.config_json,
        raw_config=payload.raw_config,
    )
    return ConfigValidateResponse(valid=valid, errors=errors, rendered_config=rendered)


@router.post("/{slug}/configs/apply", response_model=ConfigApplyResponse)
def apply_config(
    slug: str,
    payload: ConfigApplyRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> ConfigApplyResponse:
    service = _service_or_404(db, slug)
    manager = ConfigManager(db, docker_gateway)
    version, warnings = manager.apply_candidate(
        service=service, actor=current_user, payload=payload
    )

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action="config_apply",
        resource_type="service_config",
        resource_id=f"{slug}:{version.version}",
        status="success" if version.apply_status == "applied" else "failed",
        ip_address=get_client_ip(request),
        metadata_json={
            "validation_status": version.validation_status,
            "apply_status": version.apply_status,
            "warnings": warnings,
        },
        after={"service": slug, "version": version.version},
    )
    db.commit()

    return ConfigApplyResponse(
        version=ConfigVersionResponse.model_validate(version), warnings=warnings
    )


@router.post("/{slug}/configs/{version_id}/rollback", response_model=ConfigVersionResponse)
def rollback_config(
    slug: str,
    version_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> ConfigVersionResponse:
    service = _service_or_404(db, slug)
    manager = ConfigManager(db, docker_gateway)
    try:
        version = manager.rollback(service=service, actor=current_user, version_id=version_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action="config_rollback",
        resource_type="service_config",
        resource_id=f"{slug}:{version.version}",
        status="success" if version.apply_status == "applied" else "failed",
        ip_address=get_client_ip(request),
        metadata_json={"source_version_id": version_id},
    )
    db.commit()
    return ConfigVersionResponse.model_validate(version)


@router.get("/{slug}/logs")
def service_logs(
    slug: str,
    tail: int = Query(default=200, ge=10, le=5000),
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> dict[str, str]:
    service = _service_or_404(db, slug)
    logs = docker_gateway.logs(service.container_name, tail=tail)
    return {"service": slug, "logs": logs}
