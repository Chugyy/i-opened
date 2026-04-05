"""Routes for automations, steps, and logs."""

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_pool
from app.api.models.automation import (
    AutomationCreate,
    AutomationListResponse,
    AutomationResponse,
    AutomationToggle,
    AutomationUpdate,
    LogListResponse,
    LogResponse,
    PaginationMeta,
    StepCreate,
    StepListResponse,
    StepReorderInput,
    StepResponse,
    StepUpdate,
)
from app.database.crud import automation as automation_crud
from app.database.crud import automation_log as log_crud
from app.database.crud import automation_step as step_crud

router = APIRouter(prefix="/api/automations", tags=["automations"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_owner(automation: dict, user_id: str) -> None:
    if str(automation["user_id"]) != str(user_id):
        raise HTTPException(status_code=403, detail="Forbidden")


# ---------------------------------------------------------------------------
# IMPORTANT: static paths (/logs, /reorder) MUST be registered before /{id}
# ---------------------------------------------------------------------------

@router.get("/logs", response_model=LogListResponse)
async def list_all_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    lead_id: Optional[UUID] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort: Optional[str] = "scheduled_at:desc",
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    user_automations = await automation_crud.list(pool, user_id=current_user.id, calendar_id=None, trigger=None)
    automation_ids = [str(a["id"]) for a in user_automations]

    all_logs = []
    for aid in automation_ids:
        logs = await log_crud.list_by_automation(pool, automation_id=aid)
        all_logs.extend(logs)

    # Apply filters
    if lead_id:
        all_logs = [l for l in all_logs if str(l["lead_id"]) == str(lead_id)]
    if status:
        all_logs = [l for l in all_logs if l["status"] == status]
    if date_from:
        all_logs = [l for l in all_logs if str(l["scheduled_at"]) >= date_from]
    if date_to:
        all_logs = [l for l in all_logs if str(l["scheduled_at"]) <= date_to]

    # Sort
    reverse = True
    sort_key = "scheduled_at"
    if sort:
        parts = sort.split(":")
        sort_key = parts[0] if parts[0] in ("scheduled_at", "created_at") else "scheduled_at"
        reverse = parts[1] == "desc" if len(parts) > 1 else True
    all_logs.sort(key=lambda l: str(l.get(sort_key, "")), reverse=reverse)

    total = len(all_logs)
    offset = (page - 1) * limit
    page_logs = all_logs[offset: offset + limit]

    return LogListResponse(
        data=[LogResponse(**dict(l)) for l in page_logs],
        pagination=PaginationMeta(page=page, limit=limit, total=total, has_more=(offset + limit) < total),
    )


# ---------------------------------------------------------------------------
# Automations CRUD
# ---------------------------------------------------------------------------

@router.get("", response_model=AutomationListResponse)
async def list_automations(
    calendar_id: Optional[UUID] = None,
    trigger: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    rows = await automation_crud.list(pool, user_id=current_user.id, calendar_id=calendar_id, trigger=trigger)
    if is_active is not None:
        rows = [r for r in rows if r["is_active"] == is_active]
    return AutomationListResponse(data=[AutomationResponse(**dict(r)) for r in rows], total=len(rows))


@router.post("", response_model=AutomationResponse, status_code=201)
async def create_automation(
    data: AutomationCreate,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    row = await automation_crud.create(
        pool,
        id=uuid4(),
        user_id=current_user.id,
        calendar_id=data.calendar_id,
        name=data.name,
        trigger=data.trigger,
        is_active=data.is_active,
    )
    return AutomationResponse(**dict(row))


@router.get("/{automation_id}", response_model=AutomationResponse)
async def get_automation(
    automation_id: UUID,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    row = await automation_crud.get(pool, automation_id=automation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(row, current_user.id)
    return AutomationResponse(**dict(row))


@router.patch("/{automation_id}", response_model=AutomationResponse)
async def update_automation(
    automation_id: UUID,
    data: AutomationUpdate,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    row = await automation_crud.get(pool, automation_id=automation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(row, current_user.id)

    fields = data.model_dump(exclude_none=True)
    if not fields:
        return AutomationResponse(**dict(row))

    updated = await automation_crud.update(pool, automation_id=automation_id, fields=fields)
    return AutomationResponse(**dict(updated))


@router.delete("/{automation_id}", status_code=204)
async def delete_automation(
    automation_id: UUID,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    row = await automation_crud.get(pool, automation_id=automation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(row, current_user.id)
    await automation_crud.delete(pool, automation_id=automation_id)


@router.patch("/{automation_id}/toggle", response_model=AutomationResponse)
async def toggle_automation(
    automation_id: UUID,
    data: AutomationToggle,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    row = await automation_crud.get(pool, automation_id=automation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(row, current_user.id)

    # Idempotent: already at desired state
    if row["is_active"] == data.is_active:
        return AutomationResponse(**dict(row))

    if not data.is_active:
        await log_crud.cancel_pending_logs(pool, automation_id=str(automation_id))

    updated = await automation_crud.toggle_active(pool, automation_id=automation_id, is_active=data.is_active)
    return AutomationResponse(**dict(updated))


# ---------------------------------------------------------------------------
# Steps sub-resource
# ---------------------------------------------------------------------------

@router.get("/{automation_id}/steps", response_model=StepListResponse)
async def list_steps(
    automation_id: UUID,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    automation = await automation_crud.get(pool, automation_id=automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(automation, current_user.id)

    rows = await step_crud.list_by_automation(pool, automation_id=automation_id)
    return StepListResponse(data=[StepResponse(**dict(r)) for r in rows])


@router.post("/{automation_id}/steps", response_model=StepResponse, status_code=201)
async def create_step(
    automation_id: UUID,
    data: StepCreate,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    automation = await automation_crud.get(pool, automation_id=automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(automation, current_user.id)

    position = data.position
    if position is None:
        existing = await step_crud.list_by_automation(pool, automation_id=automation_id)
        position = len(existing)

    row = await step_crud.create(
        pool,
        automation_id=automation_id,
        channel=data.channel,
        delay_value=data.delay_value,
        delay_unit=data.delay_unit,
        content=data.content,
        position=position,
    )
    return StepResponse(**dict(row))


@router.patch("/{automation_id}/steps/reorder", response_model=StepListResponse)
async def reorder_steps(
    automation_id: UUID,
    data: StepReorderInput,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    automation = await automation_crud.get(pool, automation_id=automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(automation, current_user.id)

    rows = await step_crud.reorder(pool, automation_id=automation_id, ordered_ids=data.ordered_ids)
    if rows is None:
        raise HTTPException(status_code=400, detail="One or more step IDs do not belong to this automation")
    return StepListResponse(data=[StepResponse(**dict(r)) for r in rows])


@router.patch("/{automation_id}/steps/{step_id}", response_model=StepResponse)
async def update_step(
    automation_id: UUID,
    step_id: UUID,
    data: StepUpdate,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    automation = await automation_crud.get(pool, automation_id=automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(automation, current_user.id)

    step = await step_crud.get(pool, step_id=step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    if str(step["automation_id"]) != str(automation_id):
        raise HTTPException(status_code=403, detail="Step does not belong to this automation")

    fields = data.model_dump(exclude_none=True)
    if not fields:
        return StepResponse(**dict(step))

    updated = await step_crud.update(pool, step_id=step_id, fields=fields)
    return StepResponse(**dict(updated))


@router.delete("/{automation_id}/steps/{step_id}", status_code=204)
async def delete_step(
    automation_id: UUID,
    step_id: UUID,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    automation = await automation_crud.get(pool, automation_id=automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(automation, current_user.id)

    step = await step_crud.get(pool, step_id=step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    if str(step["automation_id"]) != str(automation_id):
        raise HTTPException(status_code=403, detail="Step does not belong to this automation")

    await step_crud.delete(pool, step_id=step_id)


# ---------------------------------------------------------------------------
# Logs sub-resource
# ---------------------------------------------------------------------------

@router.get("/{automation_id}/logs", response_model=LogListResponse)
async def list_automation_logs(
    automation_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    automation = await automation_crud.get(pool, automation_id=automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    _check_owner(automation, current_user.id)

    logs = await log_crud.list_by_automation(pool, automation_id=str(automation_id))
    if status:
        logs = [l for l in logs if l["status"] == status]

    total = len(logs)
    offset = (page - 1) * limit
    page_logs = logs[offset: offset + limit]

    return LogListResponse(
        data=[LogResponse(**dict(l)) for l in page_logs],
        pagination=PaginationMeta(page=page, limit=limit, total=total, has_more=(offset + limit) < total),
    )
