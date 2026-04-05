"""Endpoint tests for /api/automations."""

import pytest
import asyncpg
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_pool
from app.api.main import app
from config.config import settings

_FAKE_USER = {"sub": "00000000-0000-0000-0000-000000000001", "email": "test@example.com", "type": "access"}
_BASE = "/api/automations"


@pytest.fixture
async def pool():
    p = await asyncpg.create_pool(
        host=settings.db_host, port=settings.db_port, database=settings.db_name,
        user=settings.db_user, password=settings.db_password or "", min_size=1, max_size=3,
    )
    yield p
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM automation_logs")
        await conn.execute("DELETE FROM automation_steps")
        await conn.execute("DELETE FROM automations")
    await p.close()


@pytest.fixture
async def client(pool):
    app.dependency_overrides[get_pool] = lambda: pool
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Automation CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_automation(client):
    response = await client.post(_BASE, json={"name": "Test Auto", "trigger": "avant_rdv"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Auto"
    assert data["trigger"] == "avant_rdv"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_automation_validation_error(client):
    response = await client.post(_BASE, json={"trigger": "avant_rdv"})  # missing name
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_automation_invalid_trigger(client):
    response = await client.post(_BASE, json={"name": "Bad", "trigger": "invalid_trigger"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_automations_empty(client):
    response = await client.get(_BASE)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_automations_returns_created(client):
    await client.post(_BASE, json={"name": "A1", "trigger": "apres_rdv"})
    response = await client.get(_BASE)
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_get_automation_not_found(client):
    response = await client.get(f"{_BASE}/00000000-0000-0000-0000-000000000099")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_automation(client):
    created = (await client.post(_BASE, json={"name": "Fetch Me", "trigger": "avant_rdv"})).json()
    response = await client.get(f"{_BASE}/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_update_automation(client):
    created = (await client.post(_BASE, json={"name": "Old", "trigger": "avant_rdv"})).json()
    response = await client.patch(f"{_BASE}/{created['id']}", json={"name": "New"})
    assert response.status_code == 200
    assert response.json()["name"] == "New"


@pytest.mark.asyncio
async def test_delete_automation(client):
    created = (await client.post(_BASE, json={"name": "Del", "trigger": "avant_rdv"})).json()
    response = await client.delete(f"{_BASE}/{created['id']}")
    assert response.status_code == 204
    assert (await client.get(f"{_BASE}/{created['id']}")).status_code == 404


@pytest.mark.asyncio
async def test_toggle_automation(client):
    created = (await client.post(_BASE, json={"name": "Toggle", "trigger": "avant_rdv", "isActive": True})).json()
    response = await client.patch(f"{_BASE}/{created['id']}/toggle", json={"isActive": False})
    assert response.status_code == 200
    assert response.json()["isActive"] is False


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_step(client):
    auto = (await client.post(_BASE, json={"name": "StepAuto", "trigger": "avant_rdv"})).json()
    response = await client.post(
        f"{_BASE}/{auto['id']}/steps",
        json={"channel": "email", "delayValue": 2, "delayUnit": "hours", "content": "Hello {prenom}", "position": 0},
    )
    assert response.status_code == 201
    assert response.json()["channel"] == "email"


@pytest.mark.asyncio
async def test_list_steps_empty(client):
    auto = (await client.post(_BASE, json={"name": "NoSteps", "trigger": "avant_rdv"})).json()
    response = await client.get(f"{_BASE}/{auto['id']}/steps")
    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_create_step_invalid_channel(client):
    auto = (await client.post(_BASE, json={"name": "BadStep", "trigger": "avant_rdv"})).json()
    response = await client.post(
        f"{_BASE}/{auto['id']}/steps",
        json={"channel": "sms", "delayValue": 1, "delayUnit": "hours", "content": "x", "position": 0},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_step(client):
    auto = (await client.post(_BASE, json={"name": "DelStep", "trigger": "avant_rdv"})).json()
    step = (await client.post(
        f"{_BASE}/{auto['id']}/steps",
        json={"channel": "email", "delayValue": 1, "delayUnit": "days", "content": "Hi", "position": 0},
    )).json()
    response = await client.delete(f"{_BASE}/{auto['id']}/steps/{step['id']}")
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_automation_logs_empty(client):
    auto = (await client.post(_BASE, json={"name": "LogAuto", "trigger": "avant_rdv"})).json()
    response = await client.get(f"{_BASE}/{auto['id']}/logs")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_list_global_logs_empty(client):
    response = await client.get(f"{_BASE}/logs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], list)
