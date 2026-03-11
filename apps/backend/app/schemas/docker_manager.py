from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DockerScopeQuery(BaseModel):
    scope: Literal["project", "all"] = "project"


class DockerHostInfoResponse(BaseModel):
    docker_available: bool
    name: str = ""
    server_version: str = ""
    operating_system: str = ""
    kernel_version: str = ""
    cpu_count: int | None = None
    memory_total_bytes: int | None = None
    containers_running: int | None = None
    containers_total: int | None = None


class DockerContainerItem(BaseModel):
    id: str
    name: str
    image: str
    status: str
    state: str
    health: str = "unknown"
    created_at: datetime | None = None
    ports: list[str] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)
    project_name: str | None = None
    managed_by_project: bool
    cpu_percent: float | None = None
    memory_usage_bytes: int | None = None
    memory_limit_bytes: int | None = None
    memory_percent: float | None = None
    restart_count: int | None = None


class DockerContainersResponse(BaseModel):
    scope: Literal["project", "all"]
    items: list[DockerContainerItem] = Field(default_factory=list)


class DockerContainerActionRequest(BaseModel):
    action: Literal["start", "stop", "restart"]


class DockerContainerActionResponse(BaseModel):
    container_id: str
    action: str
    status: Literal["success", "failed"]
    message: str


class DockerImageItem(BaseModel):
    id: str
    repo_tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    size_bytes: int
    containers_using: int = 0


class DockerImagesResponse(BaseModel):
    scope: Literal["project", "all"]
    items: list[DockerImageItem] = Field(default_factory=list)


class DockerImageUpdateStatus(BaseModel):
    image_ref: str
    status: Literal["up_to_date", "update_available", "unknown", "error"]
    local_digests: list[str] = Field(default_factory=list)
    remote_digest: str | None = None
    detail: str = ""


class DockerImageUpdatesResponse(BaseModel):
    scope: Literal["project", "all"]
    items: list[DockerImageUpdateStatus] = Field(default_factory=list)


class DockerImagePullRequest(BaseModel):
    image_ref: str


class DockerImagePullResponse(BaseModel):
    image_ref: str
    status: Literal["success", "failed"]
    message: str
