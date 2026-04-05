import pytest
import asyncpg
from config.config import settings
from app.database.crud.lead import create, get_by_email_and_calendar, update, list, count_by_status, get_detail


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
        await conn.execute("DELETE FROM leads")
    await p.close()


async def test_create(pool):
    result = await create(pool, calendar_id="Calendar_Id value", first_name="First_Name value", last_name="Last_Name value", email="Email value", phone="Phone value", answers="Answers value")
    assert result["id"] is not None
    assert result["calendar_id"] == "Calendar_Id value"
    assert result["first_name"] == "First_Name value"
    assert result["last_name"] == "Last_Name value"
    assert result["email"] == "Email value"
    assert result["phone"] == "Phone value"
    assert result["answers"] == "Answers value"


async def test_update_not_found(pool):
    result = await update(pool, 999999)
    assert result is None


async def test_list_empty(pool):
    results = await list(pool)
    assert results == []


async def test_list_returns_all(pool):
    await create(pool, calendar_id="Calendar_Id test", first_name="First_Name test", last_name="Last_Name test", email="Email test", phone="Phone test", answers="Answers test")
    results = await list(pool)
    assert len(results) >= 1


async def test_count_by_status_empty(pool):
    results = await count_by_status(pool)
    assert results == []


async def test_count_by_status_returns_all(pool):
    await create(pool, calendar_id="Calendar_Id test", first_name="First_Name test", last_name="Last_Name test", email="Email test", phone="Phone test", answers="Answers test")
    results = await count_by_status(pool)
    assert len(results) >= 1

