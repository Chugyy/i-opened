import pytest
import asyncpg
from config.config import settings
from app.database.crud.calendar_sync import create, get_by_calendar, update, delete


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
        await conn.execute("DELETE FROM calendar_syncs")
    await p.close()


async def test_create(pool):
    result = await create(pool, id="Id value", calendar_id="Calendar_Id value", access_token="Access_Token value", refresh_token="Refresh_Token value", token_expiry="Token_Expiry value", sync_token="Sync_Token value")
    assert result["id"] is not None
    assert result["id"] == "Id value"
    assert result["calendar_id"] == "Calendar_Id value"
    assert result["access_token"] == "Access_Token value"
    assert result["refresh_token"] == "Refresh_Token value"
    assert result["token_expiry"] == "Token_Expiry value"
    assert result["sync_token"] == "Sync_Token value"


async def test_update_not_found(pool):
    result = await update(pool, 999999)
    assert result is None


async def test_delete(pool):
    created = await create(pool, id="Id test", calendar_id="Calendar_Id test", access_token="Access_Token test", refresh_token="Refresh_Token test", token_expiry="Token_Expiry test", sync_token="Sync_Token test")
    deleted = await delete(pool, created["id"])
    assert deleted is True


async def test_delete_not_found(pool):
    result = await delete(pool, id=999999)
    assert result is False

