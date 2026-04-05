"""Pydantic models for calendar and sub-resources."""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Literal
from datetime import datetime

from app.api.models.common import StrUUID


class BaseSchema(BaseModel):
    model_config = {"populate_by_name": True, "from_attributes": True}


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

class CalendarCreate(BaseSchema):
    name: str = Field(..., max_length=255, min_length=1, alias="name")
    description: Optional[str] = Field(None, alias="description")
    slot_duration: int = Field(..., gt=0, alias="slotDuration")

    model_config = {"populate_by_name": True, "from_attributes": True}


class CalendarUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=255, min_length=1, alias="name")
    description: Optional[str] = Field(None, alias="description")
    slot_duration: Optional[int] = Field(None, gt=0, alias="slotDuration")
    status: Optional[Literal["active", "inactive", "incomplete"]] = Field(None, alias="status")

    model_config = {"populate_by_name": True, "from_attributes": True}


class CalendarResponse(BaseSchema):
    id: StrUUID = Field(..., alias="id")
    user_id: StrUUID = Field(..., alias="userId")
    name: str
    slug: str
    description: Optional[str] = None
    slot_duration: int = Field(..., alias="slotDuration")
    status: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
        "alias_generator": None,
    }


class PaginationInfo(BaseSchema):
    current_page: int = Field(..., alias="currentPage")
    per_page: int = Field(..., alias="perPage")
    total_pages: int = Field(..., alias="totalPages")
    total_items: int = Field(..., alias="totalItems")


class CalendarListResponse(BaseSchema):
    data: List[CalendarResponse]
    pagination: PaginationInfo


class CalendarDeleteResponse(BaseSchema):
    deleted: bool
    bookings_cancelled: int = Field(..., alias="bookingsCancelled")
    automations_disabled: int = Field(..., alias="automationsDisabled")


class CalendarDeleteConfirmationRequired(BaseSchema):
    requires_confirmation: bool = Field(True, alias="requiresConfirmation")
    future_bookings_count: int = Field(..., alias="futureBookingsCount")


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

class AvailabilityInput(BaseSchema):
    day_of_week: int = Field(..., ge=0, le=6, alias="dayOfWeek")
    start_time: str = Field(..., alias="startTime", pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., alias="endTime", pattern=r"^\d{2}:\d{2}$")
    lunch_start: Optional[str] = Field(None, alias="lunchStart", pattern=r"^\d{2}:\d{2}$")
    lunch_end: Optional[str] = Field(None, alias="lunchEnd", pattern=r"^\d{2}:\d{2}$")
    is_active: bool = Field(..., alias="isActive")

    @model_validator(mode="after")
    def validate_lunch_pair(self) -> "AvailabilityInput":
        lunch_s = self.lunch_start
        lunch_e = self.lunch_end
        if (lunch_s is None) != (lunch_e is None):
            raise ValueError("lunchStart and lunchEnd must both be set or both be null")
        return self


class AvailabilityUpsertRequest(BaseSchema):
    availabilities: List[AvailabilityInput]


class AvailabilityResponse(BaseSchema):
    id: StrUUID
    calendar_id: StrUUID = Field(..., alias="calendarId")
    day_of_week: int = Field(..., alias="dayOfWeek")
    start_time: str = Field(..., alias="startTime")
    end_time: str = Field(..., alias="endTime")
    lunch_start: Optional[str] = Field(None, alias="lunchStart")
    lunch_end: Optional[str] = Field(None, alias="lunchEnd")
    is_active: bool = Field(..., alias="isActive")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class AvailabilityListResponse(BaseSchema):
    data: List[AvailabilityResponse]


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------

QUESTION_TYPES = Literal["text", "single_choice", "multiple_choice", "number"]
CHOICE_TYPES = {"single_choice", "multiple_choice"}


class QuestionCreate(BaseSchema):
    label: str = Field(..., max_length=500, min_length=1)
    type: QUESTION_TYPES
    options: Optional[List[str]] = None
    position: int = Field(..., ge=1)
    required: bool

    @model_validator(mode="after")
    def validate_options(self) -> "QuestionCreate":
        if self.type in CHOICE_TYPES and not self.options:
            raise ValueError("options is required for single_choice and multiple_choice types")
        return self


class QuestionUpdate(BaseSchema):
    label: Optional[str] = Field(None, max_length=500, min_length=1)
    type: Optional[QUESTION_TYPES] = None
    options: Optional[List[str]] = None
    position: Optional[int] = Field(None, ge=1)
    required: Optional[bool] = None


class QuestionResponse(BaseSchema):
    id: StrUUID
    calendar_id: StrUUID = Field(..., alias="calendarId")
    label: str
    type: str
    options: Optional[List[str]] = None
    position: int
    required: bool
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class QuestionListResponse(BaseSchema):
    data: List[QuestionResponse]


class QuestionReorderRequest(BaseSchema):
    ordered_ids: List[StrUUID] = Field(..., alias="orderedIds")


# ---------------------------------------------------------------------------
# QualificationRule
# ---------------------------------------------------------------------------

class RuleCreate(BaseSchema):
    question_id: StrUUID = Field(..., alias="questionId")
    disqualify_values: Optional[List[str]] = Field(None, alias="disqualifyValues")
    min_length: Optional[int] = Field(None, alias="minLength")
    contains_keywords: Optional[List[str]] = Field(None, alias="containsKeywords")
    min_value: Optional[float] = Field(None, alias="minValue")


class RuleUpdate(BaseSchema):
    disqualify_values: Optional[List[str]] = Field(None, alias="disqualifyValues")
    min_length: Optional[int] = Field(None, alias="minLength")
    contains_keywords: Optional[List[str]] = Field(None, alias="containsKeywords")
    min_value: Optional[float] = Field(None, alias="minValue")


class RuleResponse(BaseSchema):
    id: StrUUID
    calendar_id: StrUUID = Field(..., alias="calendarId")
    question_id: StrUUID = Field(..., alias="questionId")
    question_label: Optional[str] = Field(None, alias="questionLabel")
    question_type: Optional[str] = Field(None, alias="questionType")
    disqualify_values: Optional[List[str]] = Field(None, alias="disqualifyValues")
    min_length: Optional[int] = Field(None, alias="minLength")
    contains_keywords: Optional[List[str]] = Field(None, alias="containsKeywords")
    min_value: Optional[float] = Field(None, alias="minValue")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class RuleListResponse(BaseSchema):
    data: List[RuleResponse]


# ---------------------------------------------------------------------------
# CalendarSync
# ---------------------------------------------------------------------------

class GoogleConnectResponse(BaseSchema):
    authorization_url: str = Field(..., alias="authorizationUrl")
    state: str


class GoogleCallbackResponse(BaseSchema):
    calendar_id: StrUUID = Field(..., alias="calendarId")
    status: str
    events_processed: int = Field(..., alias="eventsProcessed")
    created_at: datetime = Field(..., alias="createdAt")


class SyncStatusResponse(BaseSchema):
    calendar_id: StrUUID = Field(..., alias="calendarId")
    status: str
    token_expiry: datetime = Field(..., alias="tokenExpiry")
    has_sync_token: bool = Field(..., alias="hasSyncToken")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class SyncTriggerResponse(BaseSchema):
    events_processed: int = Field(..., alias="eventsProcessed")
    slots_updated: int = Field(..., alias="slotsUpdated")
    sync_token: str = Field(..., alias="syncToken")
    status: Literal["ok", "disconnected", "no_sync_connection", "oauth_revoked"]
