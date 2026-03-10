from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReadinessCheck(BaseModel):
    name: str
    status: str
    details: str = ""


class ReadinessResponse(BaseModel):
    status: str
    timestamp: datetime
    checks: list[ReadinessCheck] = Field(default_factory=list)
