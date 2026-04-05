import pytest
import asyncpg
from config.config import settings
from app.database.crud.booking import create, update, list_by_calendar, list_by_lead, cancel, list_upcoming


@pytest.fixture
async def pool():
    p = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password or "",
        min_size=1,
        max_size=3,
    )
    yield p
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM bookings")
    await p.close()


async def test_create(pool):
    result = await create(pool, lead_id="Lead_Id value", calendar_id="Calendar_Id value", starts_at="Starts_At value", ends_at="Ends_At value", gcal_event_id="Gcal_Event_Id value")
    assert result["id"] is not None
    assert result["lead_id"] == "Lead_Id value"
    assert result["calendar_id"] == "Calendar_Id value"
    assert result["starts_at"] == "Starts_At value"
    assert result["ends_at"] == "Ends_At value"
    assert result["gcal_event_id"] == "Gcal_Event_Id value"


async def test_update_not_found(pool):
    result = await update(pool, 999999)
    assert result is None


async def test_list_by_calendar_empty(pool):
    results = await list_by_calendar(pool)
    assert results == []


async def test_list_by_calendar_returns_all(pool):
    await create(pool, lead_id="Lead_Id test", calendar_id="Calendar_Id test", starts_at="Starts_At test", ends_at="Ends_At test", gcal_event_id="Gcal_Event_Id test")
    results = await list_by_calendar(pool)
    assert len(results) >= 1


async def test_list_by_lead_empty(pool):
    results = await list_by_lead(pool)
    assert results == []


async def test_list_by_lead_returns_all(pool):
    await create(pool, lead_id="Lead_Id test", calendar_id="Calendar_Id test", starts_at="Starts_At test", ends_at="Ends_At test", gcal_event_id="Gcal_Event_Id test")
    results = await list_by_lead(pool)
    assert len(results) >= 1


async def test_cancel_not_found(pool):
    result = await cancel(pool, 999999)
    assert result is None


async def test_list_upcoming_empty(pool):
    results = await list_upcoming(pool)
    assert results == []


async def test_list_upcoming_returns_all(pool):
    await create(pool, lead_id="Lead_Id test", calendar_id="Calendar_Id test", starts_at="Starts_At test", ends_at="Ends_At test", gcal_event_id="Gcal_Event_Id test")
    results = await list_upcoming(pool)
    assert len(results) >= 1

