from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ServiceState(BaseModel):
    slug: str
    name: str
    category: str
    container_name: str
    enabled: bool
    state: str
    health: str
    uptime_seconds: int | None = None
    ports: list[str] = Field(default_factory=list)
    config_validation_status: str | None = None
    last_config_change: datetime | None = None
    last_config_version: int | None = None


class ServiceActionRequest(BaseModel):
    action: Literal["start", "stop", "restart", "reload"]


class ServiceActionResponse(BaseModel):
    slug: str
    action: str
    status: str
    message: str


class ConfigValidateRequest(BaseModel):
    config_json: dict[str, Any] = Field(default_factory=dict)
    raw_config: str = ""


class ConfigValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    rendered_config: str


class ConfigApplyRequest(BaseModel):
    config_json: dict[str, Any] = Field(default_factory=dict)
    raw_config: str = ""
    auto_reload: bool = True


class ConfigVersionResponse(BaseModel):
    id: str
    service_slug: str
    version: int
    config_json: dict[str, Any] = Field(default_factory=dict)
    raw_config: str = ""
    validation_status: str
    apply_status: str
    is_active: bool
    apply_message: str
    created_by_id: str
    created_at: datetime
    applied_at: datetime | None = None

    model_config = {"from_attributes": True}


class ConfigApplyResponse(BaseModel):
    version: ConfigVersionResponse
    warnings: list[str] = Field(default_factory=list)


class ServiceDetailResponse(BaseModel):
    service: ServiceState
    active_config: ConfigVersionResponse | None = None
