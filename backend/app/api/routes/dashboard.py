"""Routes for dashboard aggregated stats."""

import asyncio
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_pool
from app.api.models.dashboard import DashboardResponse, UpcomingBookingItem
from app.database.crud import booking as booking_crud
from app.database.crud import lead as lead_crud

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    # Run all queries in parallel
    bookings_today_task = _count_bookings_today(pool)
    leads_week_task = _count_leads_this_week(pool)
    qual_rate_task = _get_qualification_rate(pool)
    upcoming_task = booking_crud.list_upcoming(pool, calendar_id=None, limit=5)

    bookings_today, leads_this_week, qualification_rate, upcoming_rows = await asyncio.gather(
        bookings_today_task,
        leads_week_task,
        qual_rate_task,
        upcoming_task,
    )

    upcoming = [
        UpcomingBookingItem(
            booking_id=r["id"],
            lead_id=r["lead_id"],
            lead_name=r.get("lead_name") or "",
            calendar_name=r.get("calendar_name") or "",
            starts_at=r["starts_at"],
        )
        for r in (upcoming_rows or [])
    ]

    return DashboardResponse(
        bookings_today=bookings_today,
        leads_this_week=leads_this_week,
        qualification_rate=qualification_rate,
        upcoming_bookings=upcoming,
    )


async def _count_bookings_today(pool) -> int:
    from datetime import timedelta
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as cnt FROM bookings WHERE status = 'confirmed' AND starts_at >= $1 AND starts_at < $2",
            today_start, today_end,
        )
        return row["cnt"] if row else 0


async def _count_leads_this_week(pool) -> int:
    from datetime import timedelta
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as cnt FROM leads WHERE created_at >= $1",
            week_ago,
        )
        return row["cnt"] if row else 0


async def _get_qualification_rate(pool) -> float | None:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT status, COUNT(*) as cnt FROM leads GROUP BY status")
    counts = {r["status"]: int(r["cnt"]) for r in rows}
    total = sum(counts.values())
    if total == 0:
        return None
    qualifie = counts.get("qualifie", 0) + counts.get("booke", 0)
    return round(qualifie / total * 100, 2)
