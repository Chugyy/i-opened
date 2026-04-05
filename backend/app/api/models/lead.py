"""Pydantic models for lead endpoints."""

from datetime import datetime
from typing import List, Literal, Optional

from app.api.models.common import BaseSchema, StrUUID


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class LeadAnswerItem(BaseSchema):
    question_id: StrUUID
    question_label: Optional[str] = None
    value: str


class BookingItem(BaseSchema):
    id: StrUUID
    calendar_id: StrUUID
    starts_at: datetime
    ends_at: datetime
    status: str
    gcal_event_id: Optional[str] = None
    cancel_reason: Optional[str] = None
    created_at: datetime


class AutomationLogItem(BaseSchema):
    id: StrUUID
    automation_id: StrUUID
    automation_step_id: StrUUID
    trigger: str
    status: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None


class PaginationMeta(BaseSchema):
    limit: int
    offset: int
    total: int
    has_more: bool


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

class LeadListItem(BaseSchema):
    id: StrUUID
    calendar_id: StrUUID
    calendar_name: Optional[str] = None
    first_name: str
    last_name: str
    email: str
    phone: str
    status: str
    created_at: datetime


class LeadsListResponse(BaseSchema):
    data: List[LeadListItem]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class LeadStatsResponse(BaseSchema):
    nouveau: int
    qualifie: int
    non_qualifie: int
    booke: int
    no_show: int


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

class LeadDetailResponse(BaseSchema):
    id: StrUUID
    calendar_id: StrUUID
    calendar_name: Optional[str] = None
    first_name: str
    last_name: str
    email: str
    phone: str
    answers: List[LeadAnswerItem]
    status: str
    created_at: datetime
    updated_at: datetime
    bookings: List[BookingItem]
    automation_logs: List[AutomationLogItem]


# ---------------------------------------------------------------------------
# Status update
# ---------------------------------------------------------------------------

class LeadStatusUpdateRequest(BaseSchema):
    status: Literal["nouveau", "qualifie", "non_qualifie", "booke", "no_show"]


class LeadStatusUpdateResponse(BaseSchema):
    id: StrUUID
    status: str
    updated_at: datetime
