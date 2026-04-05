"""Pydantic models for dashboard endpoint."""

from datetime import datetime
from typing import List, Optional

from app.api.models.common import BaseSchema, StrUUID


class UpcomingBookingItem(BaseSchema):
    booking_id: StrUUID
    lead_id: StrUUID
    lead_name: str
    calendar_name: str
    starts_at: datetime


class DashboardResponse(BaseSchema):
    bookings_today: int
    leads_this_week: int
    qualification_rate: Optional[float] = None
    upcoming_bookings: List[UpcomingBookingItem]
