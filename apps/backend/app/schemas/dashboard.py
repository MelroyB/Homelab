from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.service import ServiceState


class DashboardOverviewResponse(BaseModel):
    generated_at: datetime
    service_count: int
    healthy_service_count: int
    degraded_service_count: int
    services: list[ServiceState] = Field(default_factory=list)
