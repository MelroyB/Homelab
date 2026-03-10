from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BackupCreateResponse(BaseModel):
    id: str
    name: str
    checksum: str
    created_at: datetime


class BackupListItem(BaseModel):
    id: str
    name: str
    checksum: str
    created_at: datetime
    restored_at: datetime | None = None


class BackupListResponse(BaseModel):
    items: list[BackupListItem] = Field(default_factory=list)


class BackupRestoreRequest(BaseModel):
    snapshot_id: str
