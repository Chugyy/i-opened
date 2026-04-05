"""Endpoint tests for /api/leads."""

import pytest
import asyncpg
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_pool
from app.api.main import app
from config.config import settings

_FAKE_USER = {"sub": "00000000-0000-0000-0000-000000000001", "email": "test@example.com", "type": "access"}
_BASE = "/api/leads"


@pytest.fixture
async def pool():
    p = await asyncpg.create_pool(
        host=settings.db_host, port=settings.db_port, database=settings.db_name,
        user=settings.db_user, password=settings.db_password or "", min_size=1, max_size=3,
    )
    yield p
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM leads")
    await p.close()


@pytest.fixture
async def client(pool):
    app.dependency_overrides[get_pool] = lambda: pool
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_leads_empty(client):
    response = await client.get(_BASE)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
    assert data["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_list_leads_pagination_params(client):
    response = await client.get(_BASE, params={"limit": 10, "offset": 0})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_leads_limit_exceeded(client):
    response = await client.get(_BASE, params={"limit": 999})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_lead_stats_empty(client):
    response = await client.get(f"{_BASE}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["nouveau"] == 0
    assert data["qualifie"] == 0
    assert data["nonQualifie"] == 0
    assert data["booke"] == 0
    assert data["noShow"] == 0


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_lead_not_found(client):
    response = await client.get(f"{_BASE}/00000000-0000-0000-0000-000000000099")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Status update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_lead_status_invalid_value(client):
    # Status must be "no_show" only — other values rejected by Pydantic
    response = await client.patch(
        f"{_BASE}/00000000-0000-0000-0000-000000000099/status",
        json={"status": "qualifie"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_lead_status_not_found(client):
    response = await client.patch(
        f"{_BASE}/00000000-0000-0000-0000-000000000099/status",
        json={"status": "no_show"},
    )
    assert response.status_code == 404
