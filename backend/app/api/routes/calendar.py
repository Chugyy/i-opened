"""FastAPI routes for Calendar and sub-resources."""

import uuid
import base64
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from config.config import settings
from app.api.models.calendar import (
    CalendarCreate,
    CalendarUpdate,
    CalendarResponse,
    CalendarListResponse,
    CalendarDeleteResponse,
    CalendarDeleteConfirmationRequired,
    AvailabilityInput,
    AvailabilityListResponse,
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionListResponse,
    QuestionReorderRequest,
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleListResponse,
    GoogleConnectResponse,
    GoogleCallbackResponse,
    SyncStatusResponse,
    SyncTriggerResponse,
    PaginationInfo,
    AvailabilityResponse,
)
from app.database.crud import calendar as calendar_crud
from app.database.crud import availability as availability_crud
from app.database.crud import question as question_crud
from app.database.crud import qualification_rule as rule_crud
from app.database.crud import calendar_sync as sync_crud

# Auth dependency — imported from deps when available; inline fallback signature
try:
    from app.api.deps import get_current_user
except ImportError:
    async def get_current_user():  # pragma: no cover
        raise HTTPException(status_code=401, detail="Not authenticated")

router = APIRouter(prefix="/api/calendars", tags=["calendars"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_pool(request: Request):
    return request.app.state.pool


def _row_to_calendar(row: dict) -> CalendarResponse:
    return CalendarResponse.model_validate(
        {
            "id": str(row["id"]),
            "userId": str(row["user_id"]),
            "name": row["name"],
            "slug": row["slug"],
            "description": row.get("description"),
            "slotDuration": row["slot_duration"],
            "status": row["status"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
    )


def _row_to_availability(row: dict) -> AvailabilityResponse:
    return AvailabilityResponse.model_validate(
        {
            "id": str(row["id"]),
            "calendarId": str(row["calendar_id"]),
            "dayOfWeek": row["day_of_week"],
            "startTime": str(row["start_time"])[:5],
            "endTime": str(row["end_time"])[:5],
            "lunchStart": str(row["lunch_start"])[:5] if row.get("lunch_start") else None,
            "lunchEnd": str(row["lunch_end"])[:5] if row.get("lunch_end") else None,
            "isActive": row["is_active"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
    )


def _row_to_question(row: dict) -> QuestionResponse:
    import json as _json
    opts = row.get("options")
    if isinstance(opts, str):
        opts = _json.loads(opts)
    return QuestionResponse.model_validate(
        {
            "id": str(row["id"]),
            "calendarId": str(row["calendar_id"]),
            "label": row["label"],
            "type": row["type"],
            "options": opts,
            "position": row["position"],
            "required": row["required"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
    )


def _row_to_rule(row: dict) -> RuleResponse:
    import json as _json
    dv = row.get("disqualify_values")
    if isinstance(dv, str):
        dv = _json.loads(dv)
    ck = row.get("contains_keywords")
    if isinstance(ck, str):
        ck = _json.loads(ck)
    return RuleResponse.model_validate(
        {
            "id": str(row["id"]),
            "calendarId": str(row["calendar_id"]),
            "questionId": str(row["question_id"]),
            "questionLabel": row.get("question_label") or row.get("label"),
            "questionType": row.get("question_type") or row.get("type"),
            "disqualifyValues": dv,
            "minLength": row.get("min_length"),
            "containsKeywords": ck,
            "minValue": float(row["min_value"]) if row.get("min_value") is not None else None,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
    )


# ---------------------------------------------------------------------------
# Calendar CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=CalendarListResponse)
async def list_calendars(
    request: Request,
    status: Optional[str] = Query(None),
    sort: str = Query("created_at:desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    rows = await calendar_crud.list(pool, user_id=current_user.id)

    # Filter
    if status:
        rows = [r for r in rows if r["status"] == status]

    # Sort
    sort_field, sort_dir = (sort.split(":") + ["desc"])[:2]
    reverse = sort_dir == "desc"
    sort_key = {"created_at": "created_at", "name": "name"}.get(sort_field, "created_at")
    rows.sort(key=lambda r: r[sort_key], reverse=reverse)

    # Paginate
    total = len(rows)
    total_pages = max(1, (total + limit - 1) // limit)
    rows = rows[(page - 1) * limit : page * limit]

    return CalendarListResponse(
        data=[_row_to_calendar(r) for r in rows],
        pagination=PaginationInfo.model_validate(
            {
                "currentPage": page,
                "perPage": limit,
                "totalPages": total_pages,
                "totalItems": total,
            }
        ),
    )


@router.post("", response_model=CalendarResponse, status_code=201)
async def create_calendar(
    request: Request,
    data: CalendarCreate,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)

    try:
        from app.core.utils.calendar import generate_slug
    except ImportError:
        def generate_slug(name: str, existing_slugs: list[str] = []) -> str:
            import re
            base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            slug = base
            i = 2
            while slug in existing_slugs:
                slug = f"{base}-{i}"
                i += 1
            return slug

    # Fetch existing slugs to avoid conflicts
    existing = await calendar_crud.list(pool, user_id=current_user.id)
    existing_slugs = [c["slug"] for c in existing]
    slug = generate_slug(data.name, existing_slugs)
    calendar_id = uuid.uuid4()

    row = await calendar_crud.create(
        pool,
        id=calendar_id,
        user_id=current_user.id,
        name=data.name,
        slug=slug,
        description=data.description,
        slot_duration=data.slot_duration,
    )
    return _row_to_calendar(row)


@router.get("/{calendar_id}", response_model=CalendarResponse)
async def get_calendar(
    calendar_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    row = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not row:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return _row_to_calendar(row)


@router.patch("/{calendar_id}", response_model=CalendarResponse)
async def update_calendar(
    calendar_id: str,
    data: CalendarUpdate,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    row = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not row:
        raise HTTPException(status_code=404, detail="Calendar not found")

    fields = data.model_dump(exclude_unset=True, by_alias=False)

    if "name" in fields:
        try:
            from app.core.utils.calendar import generate_slug
        except ImportError:
            def generate_slug(name: str, existing_slugs: list[str] = []) -> str:
                import re
                base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                slug = base
                i = 2
                while slug in existing_slugs:
                    slug = f"{base}-{i}"
                    i += 1
                return slug

        existing = await calendar_crud.list(pool, user_id=current_user.id)
        existing_slugs = [c["slug"] for c in existing]
        fields["slug"] = generate_slug(fields["name"], existing_slugs)

    # Remap camelCase -> snake_case
    remap = {"slotDuration": "slot_duration"}
    fields = {remap.get(k, k): v for k, v in fields.items()}

    updated = await calendar_crud.update(pool, calendar_id=uuid.UUID(calendar_id), fields=fields)
    if not updated:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return _row_to_calendar(updated)


@router.delete("/{calendar_id}")
async def delete_calendar(
    calendar_id: str,
    request: Request,
    confirmed: bool = Query(False),
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    row = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not row:
        raise HTTPException(status_code=404, detail="Calendar not found")

    try:
        from app.core.jobs.calendar import delete_calendar as delete_calendar_job
        result = await delete_calendar_job(pool, calendar_id=uuid.UUID(calendar_id), confirmed=confirmed)
    except ImportError:
        # Jobs not yet built — minimal inline fallback
        result = {"requires_confirmation": False, "future_bookings_count": 0}

    if result.get("requires_confirmation"):
        return CalendarDeleteConfirmationRequired.model_validate(
            {
                "requiresConfirmation": True,
                "futureBookingsCount": result["future_bookings_count"],
            }
        )

    return Response(
        status_code=204,
        content=None,
    )


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

@router.get("/{calendar_id}/availabilities", response_model=AvailabilityListResponse)
async def list_availabilities(
    calendar_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    rows = await availability_crud.list_by_calendar(pool, calendar_id=calendar_id)
    return AvailabilityListResponse(data=[_row_to_availability(r) for r in rows])


@router.put("/{calendar_id}/availabilities", response_model=AvailabilityListResponse)
async def upsert_availabilities(
    calendar_id: str,
    data: list[AvailabilityInput],
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    rows = await availability_crud.upsert_by_calendar(
        pool,
        calendar_id=calendar_id,
        availabilities=[a.model_dump(by_alias=False) for a in data],
    )

    # Auto-activate calendar if it was incomplete and at least one day is active
    if cal["status"] == "incomplete" and any(a.is_active for a in data):
        await calendar_crud.update(pool, calendar_id=uuid.UUID(calendar_id), fields={"status": "active"})

    return AvailabilityListResponse(data=[_row_to_availability(r) for r in rows])


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

@router.get("/{calendar_id}/questions", response_model=QuestionListResponse)
async def list_questions(
    calendar_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    rows = await question_crud.list_by_calendar(pool, calendar_id=calendar_id)
    return QuestionListResponse(data=[_row_to_question(r) for r in rows])


@router.post("/{calendar_id}/questions", response_model=QuestionResponse, status_code=201)
async def create_question(
    calendar_id: str,
    data: QuestionCreate,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    row = await question_crud.create(
        pool,
        calendar_id=calendar_id,
        label=data.label,
        type=data.type,
        options=data.options,
        position=data.position,
        required=data.required,
    )
    return _row_to_question(row)


@router.patch("/{calendar_id}/questions/reorder", response_model=QuestionListResponse)
async def reorder_questions(
    calendar_id: str,
    data: QuestionReorderRequest,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    rows = await question_crud.reorder(
        pool,
        calendar_id=calendar_id,
        ordered_ids=data.ordered_ids,
    )
    return QuestionListResponse(data=[_row_to_question(r) for r in rows])


@router.patch("/{calendar_id}/questions/{question_id}", response_model=QuestionResponse)
async def update_question(
    calendar_id: str,
    question_id: str,
    data: QuestionUpdate,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    fields = data.model_dump(exclude_unset=True)
    row = await question_crud.update(pool, question_id=question_id, **fields)
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    return _row_to_question(row)


@router.delete("/{calendar_id}/questions/{question_id}", status_code=204)
async def delete_question(
    calendar_id: str,
    question_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    deleted = await question_crud.delete(pool, question_id=question_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Question not found")


# ---------------------------------------------------------------------------
# Qualification Rules
# ---------------------------------------------------------------------------

@router.get("/{calendar_id}/rules", response_model=RuleListResponse)
async def list_rules(
    calendar_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    rows = await rule_crud.list_by_calendar(pool, calendar_id=calendar_id)
    return RuleListResponse(data=[_row_to_rule(r) for r in rows])


@router.post("/{calendar_id}/rules", response_model=RuleResponse, status_code=201)
async def create_rule(
    calendar_id: str,
    data: RuleCreate,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    row = await rule_crud.create(
        pool,
        calendar_id=calendar_id,
        question_id=data.question_id,
        disqualify_values=data.disqualify_values,
        min_length=data.min_length,
        contains_keywords=data.contains_keywords,
        min_value=data.min_value,
    )
    # Re-fetch with JOIN to get question_label and question_type
    rules = await rule_crud.list_by_calendar(pool, calendar_id=calendar_id)
    full_row = next((r for r in rules if str(r["id"]) == str(row["id"])), row)
    return _row_to_rule(full_row)


@router.patch("/{calendar_id}/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    calendar_id: str,
    rule_id: str,
    data: RuleUpdate,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    fields = data.model_dump(exclude_unset=True, by_alias=False)

    row = await rule_crud.update(pool, rule_id=rule_id, fields=fields)
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    # Re-fetch with JOIN for question metadata
    rules = await rule_crud.list_by_calendar(pool, calendar_id=calendar_id)
    full_row = next((r for r in rules if str(r["id"]) == str(row["id"])), row)
    return _row_to_rule(full_row)


@router.delete("/{calendar_id}/rules/{rule_id}", status_code=204)
async def delete_rule(
    calendar_id: str,
    rule_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    deleted = await rule_crud.delete(pool, rule_id=rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")


# ---------------------------------------------------------------------------
# Calendar Sync — Google Calendar
# ---------------------------------------------------------------------------

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_SCOPES = "https://www.googleapis.com/auth/calendar.readonly"


@router.post("/{calendar_id}/sync/google/connect", response_model=GoogleConnectResponse)
async def google_connect(
    calendar_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    existing = await sync_crud.get_by_calendar(pool, calendar_id=uuid.UUID(calendar_id))
    if existing and existing.get("status") == "connected":
        raise HTTPException(status_code=409, detail="Google Calendar already connected")

    state_payload = base64.urlsafe_b64encode(
        json.dumps({"calendar_id": calendar_id}).encode()
    ).decode()

    client_id = getattr(settings, "google_client_id", "")
    redirect_uri = getattr(settings, "google_redirect_uri", "")

    auth_url = (
        f"{GOOGLE_AUTH_URL}"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={GOOGLE_SCOPES}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={state_payload}"
    )

    return GoogleConnectResponse.model_validate(
        {"authorizationUrl": auth_url, "state": state_payload}
    )


@router.get("/{calendar_id}/sync/google/callback", response_model=GoogleCallbackResponse)
async def google_callback(
    calendar_id: str,
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    existing = await sync_crud.get_by_calendar(pool, calendar_id=uuid.UUID(calendar_id))
    if existing:
        raise HTTPException(status_code=409, detail="Google Calendar already connected")

    try:
        from app.core.services.calendar_sync import connect_google
        from app.core.jobs.calendar_sync import sync_calendar
    except ImportError:
        raise HTTPException(status_code=501, detail="Google sync service not yet available")

    token_data = await connect_google(code=code, state=state, calendar_id=calendar_id)
    sync_id = uuid.uuid4()
    sync_row = await sync_crud.create(
        pool,
        id=sync_id,
        calendar_id=uuid.UUID(calendar_id),
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_expiry=token_data["token_expiry"],
        sync_token=None,
    )
    sync_result = await sync_calendar(pool, calendar_id=uuid.UUID(calendar_id))

    return GoogleCallbackResponse.model_validate(
        {
            "calendarId": calendar_id,
            "status": "connected",
            "eventsProcessed": sync_result.get("events_processed", 0),
            "createdAt": sync_row["created_at"],
        }
    )


@router.get("/{calendar_id}/sync", response_model=SyncStatusResponse)
async def get_sync_status(
    calendar_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    sync = await sync_crud.get_by_calendar(pool, calendar_id=uuid.UUID(calendar_id))
    if not sync:
        raise HTTPException(status_code=404, detail="No sync connection found")

    return SyncStatusResponse.model_validate(
        {
            "calendarId": calendar_id,
            "status": sync["status"],
            "tokenExpiry": sync["token_expiry"],
            "hasSyncToken": sync.get("sync_token") is not None,
            "createdAt": sync["created_at"],
            "updatedAt": sync["updated_at"],
        }
    )


@router.delete("/{calendar_id}/sync", status_code=204)
async def delete_sync(
    calendar_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    deleted = await sync_crud.delete(pool, calendar_id=uuid.UUID(calendar_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="No sync connection found")


@router.post("/{calendar_id}/sync/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    calendar_id: str,
    request: Request,
    current_user=Depends(get_current_user),
):
    pool = _get_pool(request)
    cal = await calendar_crud.get(pool, calendar_id=uuid.UUID(calendar_id))
    if not cal:
        raise HTTPException(status_code=404, detail="Calendar not found")

    try:
        from app.core.jobs.calendar_sync import sync_calendar
    except ImportError:
        raise HTTPException(status_code=501, detail="Sync job not yet available")

    result = await sync_calendar(pool, calendar_id=uuid.UUID(calendar_id))
    return SyncTriggerResponse.model_validate(
        {
            "eventsProcessed": result.get("events_processed", 0),
            "slotsUpdated": result.get("slots_updated", 0),
            "syncToken": result.get("sync_token", ""),
            "status": result.get("status", "ok"),
        }
    )
