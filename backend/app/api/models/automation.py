"""Pydantic models for automation, automation_step, and automation_log."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import Field

from app.api.models.common import BaseSchema, StrUUID

TriggerEnum = Literal["avant_rdv", "apres_rdv", "qualifie_sans_booking", "coordonnees_sans_booking", "booking_confirme"]
ChannelEnum = Literal["email", "whatsapp"]
DelayUnitEnum = Literal["minutes", "hours", "days"]
LogStatusEnum = Literal["pending", "sent", "failed", "cancelled"]


# ---------------------------------------------------------------------------
# Automation
# ---------------------------------------------------------------------------

class AutomationCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    trigger: TriggerEnum
    calendar_id: Optional[UUID] = None
    is_active: bool = True


class AutomationUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    trigger: Optional[TriggerEnum] = None
    calendar_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class AutomationToggle(BaseSchema):
    is_active: bool


class AutomationResponse(BaseSchema):
    id: StrUUID
    user_id: StrUUID
    calendar_id: Optional[StrUUID] = None
    name: str
    trigger: TriggerEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AutomationListResponse(BaseSchema):
    data: List[AutomationResponse]
    total: int


# ---------------------------------------------------------------------------
# AutomationStep
# ---------------------------------------------------------------------------

class StepCreate(BaseSchema):
    channel: ChannelEnum
    delay_value: int = Field(..., ge=0)
    delay_unit: DelayUnitEnum
    content: str
    position: Optional[int] = Field(default=None, ge=0)


class StepUpdate(BaseSchema):
    channel: Optional[ChannelEnum] = None
    delay_value: Optional[int] = Field(default=None, ge=0)
    delay_unit: Optional[DelayUnitEnum] = None
    content: Optional[str] = None
    position: Optional[int] = Field(default=None, ge=0)


class StepResponse(BaseSchema):
    id: StrUUID
    automation_id: StrUUID
    channel: ChannelEnum
    delay_value: int
    delay_unit: DelayUnitEnum
    content: str
    position: int
    created_at: datetime
    updated_at: datetime


class StepListResponse(BaseSchema):
    data: List[StepResponse]


class StepReorderInput(BaseSchema):
    ordered_ids: List[StrUUID]


# ---------------------------------------------------------------------------
# AutomationLog
# ---------------------------------------------------------------------------

class LogResponse(BaseSchema):
    id: StrUUID
    automation_id: StrUUID
    automation_step_id: StrUUID
    lead_id: StrUUID
    trigger: TriggerEnum
    status: LogStatusEnum
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaginationMeta(BaseSchema):
    page: int
    limit: int
    total: int
    has_more: bool


class LogListResponse(BaseSchema):
    data: List[LogResponse]
    pagination: PaginationMeta
