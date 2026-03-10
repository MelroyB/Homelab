from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class BootstrapStatusResponse(BaseModel):
    bootstrap_required: bool


class BootstrapAdminRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    user: UserOut
    csrf_token: str
    access_token_expires_in: int


class RefreshResponse(BaseModel):
    csrf_token: str
    access_token_expires_in: int


class MeResponse(BaseModel):
    user: UserOut
