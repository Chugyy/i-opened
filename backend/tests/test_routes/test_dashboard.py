"""Endpoint tests for /api/dashboard."""

import pytest
import asyncpg
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_pool
from app.api.main import app
from config.config import settings

_FAKE_USER = {"sub": "00000000-0000-0000-0000-000000000001", "email": "test@example.com", "type": "access"}


@pytest.fixture
async def pool():
    p = await asyncpg.create_pool(
        host=settings.db_host, port=settings.db_port, database=settings.db_name,
        user=settings.db_user, password=settings.db_password or "", min_size=1, max_size=3,
    )
    yield p
    await p.close()


@pytest.fixture
async def client(pool):
    app.dependency_overrides[get_pool] = lambda: pool
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_dashboard(client):
    response = await client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "bookingsToday" in data
    assert "leadsThisWeek" in data
    assert "upcomingBookings" in data
    assert isinstance(data["upcomingBookings"], list)
    assert len(data["upcomingBookings"]) <= 5


@pytest.mark.asyncio
async def test_dashboard_unauthenticated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/api/dashboard")
    assert response.status_code == 403  # no Bearer token → HTTPBearer raises 403
