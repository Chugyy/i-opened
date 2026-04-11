"""Public booking flow routes — no authentication required."""

import json as _json
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.models.booking import (
    PublicCalendarResponse,
    PublicQuestionResponse,
    QualifyRequest,
    QualifyResponse,
    AvailableSlotsResponse,
    SlotItem,
    ConfirmBookingRequest,
    ConfirmBookingResponse,
)
from app.database.crud import calendar as calendar_crud
from app.database.crud import question as question_crud
from app.database.crud import lead as lead_crud
from app.database.crud import qualification_rule as rule_crud
from app.database.crud import booking as booking_crud
from app.database.crud import availability as availability_crud
from app.database.crud import user as user_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/book", tags=["book"])


def get_pool(request: Request):
    return request.app.state.pool


async def _get_active_calendar(pool, slug: str) -> dict:
    """Fetch calendar by slug, raise 404/410 as appropriate."""
    calendar = await calendar_crud.get_by_slug(pool, slug)
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    if calendar.get("status") == "inactive":
        raise HTTPException(status_code=410, detail="Calendar is no longer active")
    return calendar


async def _get_qualified_lead(pool, lead_id: str, calendar_id: str) -> dict:
    """Fetch lead, raise 404 if missing, 403 if not qualified."""
    leads = await lead_crud.list(pool, calendar_id=calendar_id, limit=1, offset=0)
    # Get lead by id — use get_detail since no get_by_id CRUD exists
    lead = await lead_crud.get_detail(pool, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.get("status") not in ("qualifie", "booke"):
        raise HTTPException(status_code=403, detail="Lead is not qualified")
    return lead


# ---------------------------------------------------------------------------
# GET /api/book/{slug}
# ---------------------------------------------------------------------------

@router.get("/{slug}", response_model=PublicCalendarResponse)
async def get_public_calendar(slug: str, request: Request):
    pool = get_pool(request)
    calendar = await _get_active_calendar(pool, slug)
    questions = await question_crud.list_by_calendar(pool, calendar_id=str(calendar["id"]))

    return PublicCalendarResponse(
        calendar_id=str(calendar["id"]),
        name=calendar["name"],
        description=calendar.get("description"),
        slot_duration=calendar["slot_duration"],
        questions=[
            PublicQuestionResponse(
                id=str(q["id"]),
                label=q["label"],
                type=q["type"],
                options=_json.loads(q["options"]) if isinstance(q.get("options"), str) else q.get("options"),
                position=q["position"],
                required=q["required"],
            )
            for q in questions
        ],
    )


# ---------------------------------------------------------------------------
# POST /api/book/{slug}/qualify
# ---------------------------------------------------------------------------

@router.post("/{slug}/qualify", response_model=QualifyResponse)
async def qualify_lead(slug: str, body: QualifyRequest, request: Request):
    pool = get_pool(request)
    calendar = await _get_active_calendar(pool, slug)
    calendar_id = str(calendar["id"])

    # Convert answers to plain dicts for CRUD
    answers = [{"question_id": a.question_id, "value": a.value} for a in body.answers]

    # Validate that referenced question_ids exist
    existing_questions = await question_crud.list_by_calendar(pool, calendar_id=calendar_id)
    existing_ids = {str(q["id"]) for q in existing_questions}
    for a in answers:
        if a["question_id"] not in existing_ids:
            raise HTTPException(status_code=422, detail=f"Unknown question_id: {a['question_id']}")

    # Blacklist: reject previously non-qualified leads
    import json
    existing = await lead_crud.get_by_email_and_calendar(pool, email=body.email, calendar_id=calendar_id)
    if existing and existing.get("status") == "non_qualifie":
        return QualifyResponse(
            lead_id=str(existing["id"]),
            status="non_qualifie",
            is_new=False,
            qualified=False,
        )

    # Upsert lead
    if existing:
        update_fields: dict = {"answers": json.dumps(answers)}
        # Only update source/UTM if provided (don't overwrite existing tracking)
        if body.source and not existing.get("source"):
            update_fields["source"] = body.source
        if body.utm_source and not existing.get("utm_source"):
            update_fields["utm_source"] = body.utm_source
        if body.utm_medium and not existing.get("utm_medium"):
            update_fields["utm_medium"] = body.utm_medium
        if body.utm_campaign and not existing.get("utm_campaign"):
            update_fields["utm_campaign"] = body.utm_campaign
        lead = await lead_crud.update(pool, lead_id=existing["id"], fields=update_fields)
        is_new = False
    else:
        lead = await lead_crud.create(
            pool,
            calendar_id=calendar_id,
            first_name=body.first_name,
            last_name=body.last_name,
            email=str(body.email),
            phone=body.phone,
            answers=json.dumps(answers),
            source=body.source,
            utm_source=body.utm_source,
            utm_medium=body.utm_medium,
            utm_campaign=body.utm_campaign,
        )
        is_new = True

    lead_id = lead["id"]

    # Evaluate qualification rules
    rules = await rule_crud.list_by_calendar(pool, calendar_id=calendar_id)
    is_qualified = _evaluate_qualification(rules, answers)
    new_status = "qualifie" if is_qualified else "non_qualifie"

    await lead_crud.update(pool, lead_id=lead_id, fields={"status": new_status})

    # Notify via Telegram on new leads
    if is_new:
        import asyncio
        from app.core.services.telegram_service import notify_new_lead
        asyncio.create_task(notify_new_lead(
            first_name=body.first_name,
            last_name=body.last_name,
            email=str(body.email),
            phone=body.phone,
            source=body.source,
            utm_medium=body.utm_medium,
            utm_campaign=body.utm_campaign,
            calendar_name=calendar.get("name", ""),
            is_qualified=is_qualified,
        ))

    return QualifyResponse(
        lead_id=str(lead_id),
        status=new_status,
        is_new=is_new,
        qualified=is_qualified,
    )


def _evaluate_qualification(rules: list[dict], answers: list[dict]) -> bool:
    """Evaluate disqualification rules. Returns True if qualified (no rule triggered)."""
    from app.core.utils.qualification_rule import evaluate_qualification
    return evaluate_qualification(rules, answers)


# ---------------------------------------------------------------------------
# GET /api/book/{slug}/slots
# ---------------------------------------------------------------------------

@router.get("/{slug}/slots", response_model=AvailableSlotsResponse)
async def get_available_slots(
    slug: str,
    request: Request,
    date: str = Query(..., description="YYYY-MM-DD"),
    lead_id: str = Query(..., alias="leadId"),
    tz: Optional[str] = Query(None, description="Prospect timezone, e.g. America/New_York"),
):
    pool = get_pool(request)
    calendar = await _get_active_calendar(pool, slug)
    calendar_id = str(calendar["id"])

    # Validate date param
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Verify lead is qualified
    await _get_qualified_lead(pool, lead_id=lead_id, calendar_id=calendar_id)

    # Get admin timezone from user table
    admin_user = await user_crud.get_by_id(pool, user_id=calendar["user_id"])
    admin_tz = admin_user.get("timezone", "Europe/Paris") if admin_user else "Europe/Paris"

    # Fetch availabilities for the day
    availabilities = await availability_crud.list_by_calendar(pool, calendar_id=calendar_id)
    day_of_week = target_date.weekday()  # 0=Monday ... 6=Sunday
    day_availability = next(
        (a for a in availabilities if a["day_of_week"] == day_of_week and a.get("is_active")),
        None,
    )

    if not day_availability:
        return AvailableSlotsResponse(date=date, slot_duration=calendar["slot_duration"], slots=[])

    # Generate theoretical slots (returns UTC-aware datetimes)
    from app.core.utils.availability import generate_slots
    slot_duration = calendar["slot_duration"]
    all_slots = generate_slots(day_availability, slot_duration=slot_duration, target_date=target_date, admin_tz=admin_tz)

    # Fetch existing bookings
    from_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    existing_bookings = await booking_crud.list_by_calendar(pool, calendar_id=calendar_id, from_dt=from_dt)

    # Fetch GCal blocked events (non-blocking)
    gcal_events: list[dict] = []
    try:
        from app.database.crud import calendar_sync as calendar_sync_crud
        gcal_sync = await calendar_sync_crud.get_by_calendar(pool, calendar_id)
        if gcal_sync and gcal_sync.get("status") == "connected":
            from app.core.services.google_calendar import fetch_events
            result = fetch_events(gcal_sync["access_token"], sync_token=gcal_sync.get("sync_token"))
            gcal_events = result.get("events", [])
    except Exception:
        logger.warning("GCal fetch failed for calendar %s — proceeding without gcal events", calendar_id)

    # Compute available slots
    available = _compute_available_slots(all_slots, existing_bookings, gcal_events, slot_duration)

    return AvailableSlotsResponse(
        date=date,
        slot_duration=slot_duration,
        slots=[
            SlotItem(
                starts_at=s if s.tzinfo else s.replace(tzinfo=timezone.utc),
                ends_at=(s + timedelta(minutes=slot_duration)) if s.tzinfo else (s + timedelta(minutes=slot_duration)).replace(tzinfo=timezone.utc),
            )
            for s in available
        ],
    )


def _to_utc_naive(dt: datetime) -> datetime:
    """Normalize any datetime to naive UTC for consistent comparison."""
    if dt.tzinfo:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _compute_available_slots(
    all_slots: list[datetime],
    bookings: list[dict],
    gcal_events: list[dict],
    slot_duration: int,
) -> list[datetime]:
    """Remove booked and gcal-blocked slots. Returns sorted list of available starts (preserving original tzinfo)."""
    booked_naive = {_to_utc_naive(b["starts_at"]) for b in bookings if b.get("starts_at")}

    available = []
    delta = timedelta(minutes=slot_duration)

    for slot_start in all_slots:
        s_naive = _to_utc_naive(slot_start)
        slot_end_naive = s_naive + delta

        # Skip if booked
        if s_naive in booked_naive:
            continue

        # Skip if overlaps with any gcal event
        blocked = False
        for event in gcal_events:
            raw_start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            raw_end = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
            if not raw_start or not raw_end:
                continue
            try:
                ev_start = _to_utc_naive(datetime.fromisoformat(raw_start))
                ev_end = _to_utc_naive(datetime.fromisoformat(raw_end))
                if s_naive < ev_end and slot_end_naive > ev_start:
                    blocked = True
                    break
            except ValueError:
                continue

        if not blocked:
            available.append(slot_start)

    return sorted(available)


# ---------------------------------------------------------------------------
# POST /api/book/{slug}/confirm
# ---------------------------------------------------------------------------

@router.post("/{slug}/confirm", response_model=ConfirmBookingResponse, status_code=201)
async def confirm_booking(slug: str, body: ConfirmBookingRequest, request: Request):
    pool = get_pool(request)
    calendar = await _get_active_calendar(pool, slug)
    calendar_id = str(calendar["id"])

    # Verify lead is qualified
    lead = await _get_qualified_lead(pool, lead_id=body.lead_id, calendar_id=calendar_id)

    # Parse starts_at
    try:
        starts_at = datetime.fromisoformat(body.starts_at)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid starts_at format. Use ISO 8601 with timezone.")

    slot_duration = calendar["slot_duration"]
    ends_at = starts_at + timedelta(minutes=slot_duration)
    target_date = starts_at.date()

    # Verify slot is still available
    availabilities = await availability_crud.list_by_calendar(pool, calendar_id=calendar_id)
    day_of_week = target_date.weekday()
    day_availability = next(
        (a for a in availabilities if a["day_of_week"] == day_of_week and a.get("is_active")),
        None,
    )

    if not day_availability:
        raise HTTPException(status_code=409, detail="No availability on selected date")

    # Get admin timezone
    admin_user = await user_crud.get_by_id(pool, user_id=calendar["user_id"])
    admin_tz = admin_user.get("timezone", "Europe/Paris") if admin_user else "Europe/Paris"

    from app.core.utils.availability import generate_slots
    all_slots = generate_slots(day_availability, slot_duration=slot_duration, target_date=target_date, admin_tz=admin_tz)

    from_dt = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    existing_bookings = await booking_crud.list_by_calendar(pool, calendar_id=calendar_id, from_dt=from_dt)

    gcal_events: list[dict] = []
    gcal_sync = None
    try:
        from app.database.crud import calendar_sync as calendar_sync_crud
        gcal_sync = await calendar_sync_crud.get_by_calendar(pool, calendar_id)
        if gcal_sync and gcal_sync.get("status") == "connected":
            from app.core.services.google_calendar import fetch_events
            result = fetch_events(gcal_sync["access_token"], sync_token=gcal_sync.get("sync_token"))
            gcal_events = result.get("events", [])
    except Exception:
        logger.warning("GCal fetch failed for calendar %s — proceeding without gcal events", calendar_id)

    available = _compute_available_slots(all_slots, existing_bookings, gcal_events, slot_duration)

    # Normalize for comparison — convert everything to UTC-naive
    starts_cmp = _to_utc_naive(starts_at) if starts_at.tzinfo else starts_at
    available_naive = [_to_utc_naive(s) if s.tzinfo else s for s in available]
    if starts_cmp not in available_naive:
        next_slots = [
            s.replace(tzinfo=timezone.utc).isoformat() if not s.tzinfo else s.isoformat()
            for s, sn in zip(available, available_naive)
            if sn > starts_cmp
        ][:5]
        raise HTTPException(
            status_code=409,
            detail={"code": "slot_taken", "next_available_slots": next_slots},
        )

    # Create booking
    booking = await booking_crud.create(
        pool,
        lead_id=body.lead_id,
        calendar_id=calendar_id,
        starts_at=starts_at,
        ends_at=ends_at,
        gcal_event_id=None,
    )

    # Update lead status to booked
    from uuid import UUID as _UUID
    await lead_crud.update(pool, lead_id=_UUID(body.lead_id), fields={"status": "booke"})

    # Non-blocking: push to Google Calendar
    gcal_event_id: Optional[str] = None
    if gcal_sync and gcal_sync.get("status") == "connected":
        try:
            from app.core.services.google_calendar import push_event
            result = push_event(
                gcal_sync["access_token"],
                {
                    "id": booking["id"],
                    "start_time": starts_at,
                    "end_time": ends_at,
                    "prospect_email": lead.get("email"),
                    "prospect_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                },
            )
            gcal_event_id = result.get("google_event_id")
            if gcal_event_id:
                await booking_crud.update(
                    pool,
                    booking_id=str(booking["id"]),
                    gcal_event_id=gcal_event_id,
                    status=None,
                    cancel_reason=None,
                )
        except Exception:
            logger.warning("GCal push failed for booking %s — non-blocking", booking["id"])

    # Schedule automations (all notifications go through automations — no hardcoded emails)
    try:
        from app.core.jobs.automation_log import schedule_automation, cancel_pending_for_lead

        # Cancel "sans_booking" automations (prospect has booked)
        await cancel_pending_for_lead(pool, lead_id=body.lead_id, triggers=["coordonnees_sans_booking", "qualifie_sans_booking"])

        # Schedule "booking_confirme" automations
        await schedule_automation(pool, lead_id=body.lead_id, trigger="booking_confirme", calendar_id=calendar_id, booking=dict(booking))

        # Schedule "avant_rdv" automations
        await schedule_automation(pool, lead_id=body.lead_id, trigger="avant_rdv", calendar_id=calendar_id, booking=dict(booking))

        # Schedule "apres_rdv" automations
        await schedule_automation(pool, lead_id=body.lead_id, trigger="apres_rdv", calendar_id=calendar_id, booking=dict(booking))
        # Execute instant automations (delay=0) immediately
        from app.core.jobs.automation_log import process_automation_queue
        await process_automation_queue(pool)
    except Exception as e:
        logger.warning("Automation scheduling failed for booking %s: %s", booking["id"], e)

    return ConfirmBookingResponse(
        booking_id=str(booking["id"]),
        lead_id=body.lead_id,
        calendar_id=calendar_id,
        starts_at=booking["starts_at"],
        ends_at=booking["ends_at"],
        status="confirmed",
        gcal_event_id=gcal_event_id,
        emails_sent=False,  # handled by automation worker
        created_at=booking["created_at"],
    )
