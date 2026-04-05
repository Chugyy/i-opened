import pytest
import asyncpg
from config.config import settings
from app.database.crud.calendar import create, get, get_by_slug, update, delete, list


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
        await conn.execute("DELETE FROM calendars")
    await p.close()


async def test_create(pool):
    result = await create(pool, id="Id value", user_id="User_Id value", name="Name value", slug="Slug value", description="Description value", slot_duration="Slot_Duration value")
    assert result["id"] is not None
    assert result["id"] == "Id value"
    assert result["user_id"] == "User_Id value"
    assert result["name"] == "Name value"
    assert result["slug"] == "Slug value"
    assert result["description"] == "Description value"
    assert result["slot_duration"] == "Slot_Duration value"


async def test_update_not_found(pool):
    result = await update(pool, 999999)
    assert result is None


async def test_delete(pool):
    created = await create(pool, id="Id test", user_id="User_Id test", name="Name test", slug="Slug test", description="Description test", slot_duration="Slot_Duration test")
    deleted = await delete(pool, created["id"])
    assert deleted is True


async def test_delete_not_found(pool):
    result = await delete(pool, id=999999)
    assert result is False


async def test_list_empty(pool):
    results = await list(pool)
    assert results == []


async def test_list_returns_all(pool):
    await create(pool, id="Id test", user_id="User_Id test", name="Name test", slug="Slug test", description="Description test", slot_duration="Slot_Duration test")
    results = await list(pool)
    assert len(results) >= 1

