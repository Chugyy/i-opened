"""Pydantic models for user / auth endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field

from app.api.models.common import BaseSchema, StrUUID


class SetupAdminRequest(BaseSchema):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class RefreshRequest(BaseSchema):
    refresh_token: str


class UpdateProfileRequest(BaseSchema):
    full_name: Optional[str] = Field(None, min_length=1)
    notifications_enabled: Optional[bool] = None
    timezone: Optional[str] = None


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserProfileResponse(BaseSchema):
    id: StrUUID
    email: str
    full_name: str
    notifications_enabled: bool
    timezone: str
    created_at: datetime
    updated_at: datetime
