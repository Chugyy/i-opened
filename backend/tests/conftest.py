"""Shared test fixtures."""

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from config.config import settings


@pytest_asyncio.fixture
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
    await p.close()


@pytest_asyncio.fixture
async def client(pool):
    app.state.pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM users")
