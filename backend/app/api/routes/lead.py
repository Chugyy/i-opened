"""Routes for leads."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_pool
from app.api.models.lead import (
    LeadDetailResponse,
    LeadStatsResponse,
    LeadStatusUpdateRequest,
    LeadStatusUpdateResponse,
    LeadsListResponse,
    LeadListItem,
    PaginationMeta,
)
from app.database.crud import lead as lead_crud

router = APIRouter(prefix="/api/leads", tags=["leads"])


# IMPORTANT: /stats must be registered before /{lead_id}

@router.get("/stats", response_model=LeadStatsResponse)
async def get_lead_stats(
    calendar_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    rows = await lead_crud.count_by_status(pool, calendar_id=calendar_id)
    counts = {r["status"]: r["count"] for r in rows}
    return LeadStatsResponse(
        nouveau=counts.get("nouveau", 0),
        qualifie=counts.get("qualifie", 0),
        non_qualifie=counts.get("non_qualifie", 0),
        booke=counts.get("booke", 0),
        no_show=counts.get("no_show", 0),
    )


@router.get("", response_model=LeadsListResponse)
async def list_leads(
    status: Optional[str] = None,
    calendar_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    rows = await lead_crud.list(
        pool,
        calendar_id=calendar_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    total = len(rows)
    return LeadsListResponse(
        data=[LeadListItem(**dict(r)) for r in rows],
        pagination=PaginationMeta(
            limit=limit,
            offset=offset,
            total=total,
            has_more=(offset + limit) < total,
        ),
    )


@router.get("/{lead_id}", response_model=LeadDetailResponse)
async def get_lead(
    lead_id: str,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    import json as _json
    from app.database.crud import booking as booking_crud
    from app.database.crud import automation_log as log_crud

    from uuid import UUID as _UUID
    lid = _UUID(lead_id)

    row = await lead_crud.get_detail(pool, lead_id=lid)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead = dict(row)
    # Parse JSONB answers (may be double-encoded)
    answers = lead.get("answers", [])
    if isinstance(answers, str):
        answers = _json.loads(answers)
    if isinstance(answers, str):
        answers = _json.loads(answers)

    # Enrich answers with question labels
    if answers:
        question_ids = [_UUID(a["questionId"]) if "questionId" in a else _UUID(a["question_id"]) for a in answers]
        async with pool.acquire() as conn:
            q_rows = await conn.fetch("SELECT id, label FROM questions WHERE id = ANY($1)", question_ids)
        label_map = {str(r["id"]): r["label"] for r in q_rows}
        for a in answers:
            qid = a.get("questionId") or a.get("question_id")
            a["questionLabel"] = label_map.get(str(qid))

    # Fetch related bookings
    bookings_rows = await booking_crud.list_by_lead(pool, lead_id=lid)
    # Fetch related automation logs
    logs_rows = await log_crud.list_by_lead(pool, lead_id=lid)

    return LeadDetailResponse(
        id=lead["id"],
        calendar_id=lead["calendar_id"],
        calendar_name=lead.get("calendar_name"),
        first_name=lead["first_name"],
        last_name=lead["last_name"],
        email=lead["email"],
        phone=lead["phone"],
        answers=answers,
        status=lead["status"],
        created_at=lead["created_at"],
        updated_at=lead["updated_at"],
        bookings=bookings_rows or [],
        automation_logs=logs_rows or [],
    )


@router.patch("/{lead_id}/status", response_model=LeadStatusUpdateResponse)
async def update_lead_status(
    lead_id: str,
    data: LeadStatusUpdateRequest,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    from uuid import UUID as _UUID
    lid = _UUID(lead_id)

    existing = await lead_crud.get_detail(pool, lead_id=lid)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")

    updated = await lead_crud.update(pool, lead_id=lid, fields={"status": data.status})
    return LeadStatusUpdateResponse(
        id=str(updated["id"]),
        status=updated["status"],
        updated_at=str(updated["updated_at"]),
    )


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: str,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    from uuid import UUID as _UUID
    lid = _UUID(lead_id)

    existing = await lead_crud.get_detail(pool, lead_id=lid)
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")

    await lead_crud.delete(pool, lead_id=lid)
    return None
