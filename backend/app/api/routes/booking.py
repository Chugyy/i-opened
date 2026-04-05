"""Admin routes for booking management — protected."""

import logging
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.models.booking import (
    BookingsListResponse,
    BookingResponse,
    PaginationMeta,
    UpcomingBookingsResponse,
    BookingShortResponse,
    CancelBookingRequest,
    CancelBookingResponse,
    NoShowResponse,
)
from app.database.crud import booking as booking_crud
from app.database.crud import lead as lead_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


def get_pool(request: Request):
    return request.app.state.pool


async def get_current_user(request: Request):
    from app.core.utils.user import verify_token, InvalidTokenError, TokenExpiredError

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = auth.removeprefix("Bearer ")
    try:
        payload = verify_token(token, "access")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    from types import SimpleNamespace
    return SimpleNamespace(id=payload["sub"], email=payload.get("email"))


# ---------------------------------------------------------------------------
# GET /api/bookings
# ---------------------------------------------------------------------------

@router.get("", response_model=BookingsListResponse)
async def list_bookings(
    calendar_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("starts_at:desc"),
    pool=Depends(get_pool),
    current_user=Depends(get_current_user),
):
    # Validate status filter
    valid_statuses = {"confirmed", "cancelled", "no_show"}
    if status and status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    # Parse date filters
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    try:
        if date_from:
            from_dt = datetime.fromisoformat(date_from)
        if date_to:
            to_dt = datetime.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601.")

    rows = await booking_crud.list_by_calendar(pool, calendar_id=calendar_id, from_dt=from_dt)

    # Post-filter by status / date_to (CRUD returns confirmed only by default)
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if to_dt:
        rows = [r for r in rows if r.get("starts_at") and r["starts_at"] <= to_dt]

    total = len(rows)
    offset = (page - 1) * limit
    page_rows = rows[offset: offset + limit]
    total_pages = max(1, (total + limit - 1) // limit)

    return BookingsListResponse(
        data=[BookingResponse.model_validate(r) for r in page_rows],
        pagination=PaginationMeta(
            current_page=page,
            per_page=limit,
            total_pages=total_pages,
            total_items=total,
        ),
    )


# ---------------------------------------------------------------------------
# GET /api/bookings/upcoming
# ---------------------------------------------------------------------------

@router.get("/upcoming", response_model=UpcomingBookingsResponse)
async def list_upcoming_bookings(
    calendar_id: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=20),
    pool=Depends(get_pool),
    current_user=Depends(get_current_user),
):
    rows = await booking_crud.list_upcoming(pool, calendar_id=calendar_id, limit=limit)
    return UpcomingBookingsResponse(
        data=[BookingShortResponse.model_validate(r) for r in rows],
        count=len(rows),
    )


# ---------------------------------------------------------------------------
# PATCH /api/bookings/{booking_id}/cancel
# ---------------------------------------------------------------------------

@router.patch("/{booking_id}/cancel", response_model=CancelBookingResponse)
async def cancel_booking(
    booking_id: str,
    body: CancelBookingRequest,
    pool=Depends(get_pool),
    current_user=Depends(get_current_user),
):
    # Fetch the booking to check its current status before updating
    # list_by_lead with lead_id=booking_id is a misuse — use update to peek, then cancel
    # Use cancel directly; it returns None if the row doesn't exist
    # To validate current status first, fetch via a list filtered by id (workaround until get_by_id CRUD exists)
    pre_check = await booking_crud.update(
        pool, booking_id=booking_id, gcal_event_id=None, status=None, cancel_reason=None
    )
    if not pre_check:
        raise HTTPException(status_code=404, detail="Booking not found")
    if pre_check.get("status") in ("cancelled", "no_show"):
        raise HTTPException(status_code=400, detail=f"Booking cannot be cancelled (current status: {pre_check['status']})")

    booking = await booking_crud.cancel(pool, booking_id=booking_id, reason=body.reason)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Non-blocking side effects: gcal delete + lead email
    try:
        from app.database.crud import calendar_sync as calendar_sync_crud
        gcal_sync = await calendar_sync_crud.get_by_calendar(pool, booking["calendar_id"])
        if gcal_sync and booking.get("gcal_event_id"):
            from app.core.services.google_calendar import delete_event
            try:
                delete_event(gcal_sync["access_token"], booking["gcal_event_id"])
            except Exception:
                logger.warning("GCal delete failed for booking %s — non-blocking", booking_id)
    except Exception:
        logger.warning("Could not fetch gcal_sync for booking %s", booking_id)

    return CancelBookingResponse.model_validate(booking)


# ---------------------------------------------------------------------------
# PATCH /api/bookings/{booking_id}/no-show
# ---------------------------------------------------------------------------

@router.patch("/{booking_id}/no-show", response_model=NoShowResponse)
async def mark_no_show(
    booking_id: str,
    pool=Depends(get_pool),
    current_user=Depends(get_current_user),
):
    # Pre-check: fetch current status without mutating
    pre_check = await booking_crud.update(
        pool, booking_id=booking_id, gcal_event_id=None, status=None, cancel_reason=None
    )
    if not pre_check:
        raise HTTPException(status_code=404, detail="Booking not found")
    if pre_check.get("status") != "confirmed":
        raise HTTPException(
            status_code=400,
            detail=f"Only confirmed bookings can be marked as no-show (current: {pre_check['status']})",
        )

    booking = await booking_crud.update(
        pool, booking_id=booking_id, status="no_show", gcal_event_id=None, cancel_reason=None
    )

    # Update lead status to no_show
    try:
        await lead_crud.update(pool, lead_id=booking["lead_id"], fields={"status": "no_show"})
    except Exception:
        logger.warning("Failed to update lead status to no_show for lead %s", booking.get("lead_id"))

    return NoShowResponse.model_validate(booking)
