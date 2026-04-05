import pytest
import asyncpg
from config.config import settings
from app.database.crud.automation_log import create, update_status, list_pending, list_by_lead, list_by_automation, cancel_by_lead_and_trigger, cancel_pending_logs


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
        await conn.execute("DELETE FROM automation_logs")
    await p.close()


async def test_create(pool):
    result = await create(pool, automation_id="Automation_Id value", automation_step_id="Automation_Step_Id value", lead_id="Lead_Id value", trigger="Trigger value", scheduled_at="Scheduled_At value")
    assert result["id"] is not None
    assert result["automation_id"] == "Automation_Id value"
    assert result["automation_step_id"] == "Automation_Step_Id value"
    assert result["lead_id"] == "Lead_Id value"
    assert result["trigger"] == "Trigger value"
    assert result["scheduled_at"] == "Scheduled_At value"


async def test_update_status_not_found(pool):
    result = await update_status(pool, 999999)
    assert result is None


async def test_list_pending_empty(pool):
    results = await list_pending(pool)
    assert results == []


async def test_list_pending_returns_all(pool):
    await create(pool, automation_id="Automation_Id test", automation_step_id="Automation_Step_Id test", lead_id="Lead_Id test", trigger="Trigger test", scheduled_at="Scheduled_At test")
    results = await list_pending(pool)
    assert len(results) >= 1


async def test_list_by_lead_empty(pool):
    results = await list_by_lead(pool)
    assert results == []


async def test_list_by_lead_returns_all(pool):
    await create(pool, automation_id="Automation_Id test", automation_step_id="Automation_Step_Id test", lead_id="Lead_Id test", trigger="Trigger test", scheduled_at="Scheduled_At test")
    results = await list_by_lead(pool)
    assert len(results) >= 1


async def test_list_by_automation_empty(pool):
    results = await list_by_automation(pool)
    assert results == []


async def test_list_by_automation_returns_all(pool):
    await create(pool, automation_id="Automation_Id test", automation_step_id="Automation_Step_Id test", lead_id="Lead_Id test", trigger="Trigger test", scheduled_at="Scheduled_At test")
    results = await list_by_automation(pool)
    assert len(results) >= 1


async def test_cancel_by_lead_and_trigger_not_found(pool):
    result = await cancel_by_lead_and_trigger(pool, 999999)
    assert result is None


async def test_cancel_pending_logs_not_found(pool):
    result = await cancel_pending_logs(pool, 999999)
    assert result is None

