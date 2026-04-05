import pytest
import asyncpg
from config.config import settings
from app.database.crud.question import create, update, delete, list_by_calendar, reorder


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
        await conn.execute("DELETE FROM questions")
    await p.close()


async def test_create(pool):
    result = await create(pool, calendar_id="Calendar_Id value", label="Label value", type="Type value", options="Options value", position="Position value", required="Required value")
    assert result["id"] is not None
    assert result["calendar_id"] == "Calendar_Id value"
    assert result["label"] == "Label value"
    assert result["type"] == "Type value"
    assert result["options"] == "Options value"
    assert result["position"] == "Position value"
    assert result["required"] == "Required value"


async def test_update_not_found(pool):
    result = await update(pool, 999999)
    assert result is None


async def test_delete(pool):
    created = await create(pool, calendar_id="Calendar_Id test", label="Label test", type="Type test", options="Options test", position="Position test", required="Required test")
    deleted = await delete(pool, created["id"])
    assert deleted is True


async def test_delete_not_found(pool):
    result = await delete(pool, id=999999)
    assert result is False


async def test_list_by_calendar_empty(pool):
    results = await list_by_calendar(pool)
    assert results == []


async def test_list_by_calendar_returns_all(pool):
    await create(pool, calendar_id="Calendar_Id test", label="Label test", type="Type test", options="Options test", position="Position test", required="Required test")
    results = await list_by_calendar(pool)
    assert len(results) >= 1


async def test_reorder_not_found(pool):
    result = await reorder(pool, 999999)
    assert result is None

