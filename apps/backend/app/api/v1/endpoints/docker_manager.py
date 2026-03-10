from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_docker_gateway, get_settings_dep, require_admin
from app.core.config import Settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.docker_manager import (
    DockerContainerActionRequest,
    DockerContainerActionResponse,
    DockerContainersResponse,
    DockerHostInfoResponse,
    DockerImagePullRequest,
    DockerImagePullResponse,
    DockerImagesResponse,
    DockerImageUpdatesResponse,
)
from app.services.audit.service import AuditService
from app.services.docker_gateway import DockerGateway
from app.services.docker_manager import DockerManagerService

router = APIRouter()


@router.get("/host", response_model=DockerHostInfoResponse)
def docker_host_info(
    _admin_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
    settings: Settings = Depends(get_settings_dep),
) -> DockerHostInfoResponse:
    manager = DockerManagerService(docker_gateway, settings)
    return manager.host_info()


@router.get("/containers", response_model=DockerContainersResponse)
def docker_containers(
    scope: str = Query(default="project", pattern="^(project|all)$"),
    _admin_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
    settings: Settings = Depends(get_settings_dep),
) -> DockerContainersResponse:
    manager = DockerManagerService(docker_gateway, settings)
    return DockerContainersResponse(scope=scope, items=manager.list_containers(scope=scope))


@router.post("/containers/{container_id}/actions", response_model=DockerContainerActionResponse)
def docker_container_action(
    container_id: str,
    payload: DockerContainerActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
    settings: Settings = Depends(get_settings_dep),
) -> DockerContainerActionResponse:
    manager = DockerManagerService(docker_gateway, settings)
    ok, message = manager.container_action(container_id, payload.action)

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action=f"docker_container_{payload.action}",
        resource_type="docker_container",
        resource_id=container_id,
        status="success" if ok else "failed",
        ip_address=get_client_ip(request),
        metadata_json={"message": message},
    )
    db.commit()

    return DockerContainerActionResponse(
        container_id=container_id,
        action=payload.action,
        status="success" if ok else "failed",
        message=message,
    )


@router.get("/images", response_model=DockerImagesResponse)
def docker_images(
    scope: str = Query(default="project", pattern="^(project|all)$"),
    _admin_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
    settings: Settings = Depends(get_settings_dep),
) -> DockerImagesResponse:
    manager = DockerManagerService(docker_gateway, settings)
    return DockerImagesResponse(scope=scope, items=manager.list_images(scope=scope))


@router.get("/images/updates", response_model=DockerImageUpdatesResponse)
def docker_image_updates(
    scope: str = Query(default="project", pattern="^(project|all)$"),
    _admin_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
    settings: Settings = Depends(get_settings_dep),
) -> DockerImageUpdatesResponse:
    manager = DockerManagerService(docker_gateway, settings)
    return DockerImageUpdatesResponse(scope=scope, items=manager.check_updates(scope=scope))


@router.post("/images/pull", response_model=DockerImagePullResponse)
def docker_image_pull(
    payload: DockerImagePullRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
    settings: Settings = Depends(get_settings_dep),
) -> DockerImagePullResponse:
    manager = DockerManagerService(docker_gateway, settings)
    ok, message = manager.pull_image(image_ref=payload.image_ref)

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action="docker_image_pull",
        resource_type="docker_image",
        resource_id=payload.image_ref,
        status="success" if ok else "failed",
        ip_address=get_client_ip(request),
        metadata_json={"message": message},
    )
    db.commit()

    return DockerImagePullResponse(
        image_ref=payload.image_ref,
        status="success" if ok else "failed",
        message=message,
    )
