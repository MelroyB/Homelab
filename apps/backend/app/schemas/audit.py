from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuditEventResponse(BaseModel):
    id: str
    actor_user_id: str | None
    action: str
    resource_type: str
    resource_id: str
    status: str
    ip_address: str | None
    before: dict
    after: dict
    metadata_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditListResponse(BaseModel):
    items: list[AuditEventResponse] = Field(default_factory=list)
