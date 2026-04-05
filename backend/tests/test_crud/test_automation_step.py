import pytest
import asyncpg
from config.config import settings
from app.database.crud.automation_step import get, create, update, delete, list_by_automation, reorder


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
        await conn.execute("DELETE FROM automation_steps")
    await p.close()


async def test_create(pool):
    result = await create(pool, automation_id="Automation_Id value", channel="Channel value", delay_value="Delay_Value value", delay_unit="Delay_Unit value", content="Content value", position="Position value")
    assert result["id"] is not None
    assert result["automation_id"] == "Automation_Id value"
    assert result["channel"] == "Channel value"
    assert result["delay_value"] == "Delay_Value value"
    assert result["delay_unit"] == "Delay_Unit value"
    assert result["content"] == "Content value"
    assert result["position"] == "Position value"


async def test_update_not_found(pool):
    result = await update(pool, 999999)
    assert result is None


async def test_delete(pool):
    created = await create(pool, automation_id="Automation_Id test", channel="Channel test", delay_value="Delay_Value test", delay_unit="Delay_Unit test", content="Content test", position="Position test")
    deleted = await delete(pool, created["id"])
    assert deleted is True


async def test_delete_not_found(pool):
    result = await delete(pool, id=999999)
    assert result is False


async def test_list_by_automation_empty(pool):
    results = await list_by_automation(pool)
    assert results == []


async def test_list_by_automation_returns_all(pool):
    await create(pool, automation_id="Automation_Id test", channel="Channel test", delay_value="Delay_Value test", delay_unit="Delay_Unit test", content="Content test", position="Position test")
    results = await list_by_automation(pool)
    assert len(results) >= 1


async def test_reorder_not_found(pool):
    result = await reorder(pool, 999999)
    assert result is None

