import pytest
import asyncpg
from config.config import settings
from app.database.crud.availability import upsert_by_calendar, list_by_calendar


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
        await conn.execute("DELETE FROM availabilities")
    await p.close()


async def test_list_by_calendar_empty(pool):
    results = await list_by_calendar(pool)
    assert results == []

