"""Pydantic models for booking — admin + public booking flow."""

from typing import Optional, List, Literal
from datetime import datetime

from pydantic import EmailStr, Field

from app.api.models.common import BaseSchema, StrUUID


# ---------------------------------------------------------------------------
# Shared / nested
# ---------------------------------------------------------------------------

class PaginationMeta(BaseSchema):
    current_page: int = Field(..., alias="currentPage")
    per_page: int = Field(..., alias="perPage")
    total_pages: int = Field(..., alias="totalPages")
    total_items: int = Field(..., alias="totalItems")


class BookingResponse(BaseSchema):
    id: StrUUID
    lead_id: StrUUID = Field(..., alias="leadId")
    calendar_id: StrUUID = Field(..., alias="calendarId")
    starts_at: datetime = Field(..., alias="startsAt")
    ends_at: datetime = Field(..., alias="endsAt")
    status: Literal["confirmed", "cancelled", "no_show"]
    gcal_event_id: Optional[str] = Field(None, alias="gcalEventId")
    cancel_reason: Optional[str] = Field(None, alias="cancelReason")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class BookingShortResponse(BaseSchema):
    id: StrUUID
    lead_id: StrUUID = Field(..., alias="leadId")
    calendar_id: StrUUID = Field(..., alias="calendarId")
    starts_at: datetime = Field(..., alias="startsAt")
    ends_at: datetime = Field(..., alias="endsAt")
    status: str
    gcal_event_id: Optional[str] = Field(None, alias="gcalEventId")
    created_at: datetime = Field(..., alias="createdAt")


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

class BookingsListResponse(BaseSchema):
    data: List[BookingResponse]
    pagination: PaginationMeta


class UpcomingBookingsResponse(BaseSchema):
    data: List[BookingShortResponse]
    count: int


class CancelBookingRequest(BaseSchema):
    reason: Optional[str] = None


class CancelBookingResponse(BaseSchema):
    id: StrUUID
    lead_id: StrUUID = Field(..., alias="leadId")
    calendar_id: StrUUID = Field(..., alias="calendarId")
    starts_at: datetime = Field(..., alias="startsAt")
    ends_at: datetime = Field(..., alias="endsAt")
    status: Literal["cancelled"]
    cancel_reason: Optional[str] = Field(None, alias="cancelReason")
    updated_at: datetime = Field(..., alias="updatedAt")


class NoShowResponse(BaseSchema):
    id: StrUUID
    lead_id: StrUUID = Field(..., alias="leadId")
    calendar_id: StrUUID = Field(..., alias="calendarId")
    starts_at: datetime = Field(..., alias="startsAt")
    ends_at: datetime = Field(..., alias="endsAt")
    status: Literal["no_show"]
    updated_at: datetime = Field(..., alias="updatedAt")


# ---------------------------------------------------------------------------
# Public booking flow
# ---------------------------------------------------------------------------

class PublicQuestionResponse(BaseSchema):
    id: StrUUID
    label: str
    type: Literal["text", "single_choice", "multiple_choice", "number"]
    options: Optional[List[str]] = None
    position: int
    required: bool


class PublicCalendarResponse(BaseSchema):
    calendar_id: StrUUID = Field(..., alias="calendarId")
    name: str
    description: Optional[str] = None
    slot_duration: int = Field(..., alias="slotDuration")
    questions: List[PublicQuestionResponse]


class AnswerInput(BaseSchema):
    question_id: StrUUID = Field(..., alias="questionId")
    value: str


class QualifyRequest(BaseSchema):
    first_name: str = Field(..., min_length=1, alias="firstName")
    last_name: str = Field(..., min_length=1, alias="lastName")
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+[1-9]\d{7,14}$")
    answers: List[AnswerInput] = Field(default_factory=list)
    source: Optional[str] = Field(None, max_length=100)
    utm_source: Optional[str] = Field(None, alias="utmSource", max_length=100)
    utm_medium: Optional[str] = Field(None, alias="utmMedium", max_length=100)
    utm_campaign: Optional[str] = Field(None, alias="utmCampaign", max_length=100)


class QualifyResponse(BaseSchema):
    lead_id: StrUUID = Field(..., alias="leadId")
    status: Literal["qualifie", "non_qualifie"]
    is_new: bool = Field(..., alias="isNew")
    qualified: bool


class SlotItem(BaseSchema):
    starts_at: datetime = Field(..., alias="startsAt")
    ends_at: datetime = Field(..., alias="endsAt")


class AvailableSlotsResponse(BaseSchema):
    date: str  # YYYY-MM-DD
    slot_duration: int = Field(..., alias="slotDuration")
    slots: List[SlotItem]


class ConfirmBookingRequest(BaseSchema):
    lead_id: StrUUID = Field(..., alias="leadId")
    starts_at: str = Field(..., alias="startsAt")  # ISO 8601 timezone-aware


class ConfirmBookingResponse(BaseSchema):
    booking_id: StrUUID = Field(..., alias="bookingId")
    lead_id: StrUUID = Field(..., alias="leadId")
    calendar_id: StrUUID = Field(..., alias="calendarId")
    starts_at: datetime = Field(..., alias="startsAt")
    ends_at: datetime = Field(..., alias="endsAt")
    status: Literal["confirmed"]
    gcal_event_id: Optional[str] = Field(None, alias="gcalEventId")
    emails_sent: bool = Field(..., alias="emailsSent")
    created_at: datetime = Field(..., alias="createdAt")
