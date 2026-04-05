"""Endpoint tests for /api/auth."""

import pytest
from httpx import AsyncClient

ADMIN_PAYLOAD = {
    "email": "admin@test.com",
    "password": "securepass123",
    "fullName": "Test Admin",
}


# ---------------------------------------------------------------------------
# POST /api/auth/setup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_setup_admin_creates_account(client: AsyncClient):
    response = await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["tokenType"] == "bearer"


@pytest.mark.asyncio
async def test_setup_admin_conflict(client: AsyncClient):
    await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    response = await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_setup_admin_validation_error(client: AsyncClient):
    response = await client.post("/api/auth/setup", json={"email": "bad", "password": "short"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    response = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": ADMIN_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    response = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_PAYLOAD["email"], "password": "wrongpass"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    response = await client.post(
        "/api/auth/login",
        json={"email": "nobody@test.com", "password": "anypass"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/auth/refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient):
    setup = await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    refresh_token = setup.json()["refreshToken"]
    response = await client.post("/api/auth/refresh", json={"refreshToken": refresh_token})
    assert response.status_code == 200
    assert "accessToken" in response.json()


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    response = await client.post("/api/auth/refresh", json={"refreshToken": "not.a.token"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient):
    setup = await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    access_token = setup.json()["accessToken"]
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == ADMIN_PAYLOAD["email"]
    assert data["fullName"] == ADMIN_PAYLOAD["fullName"]
    assert "id" in data
    assert "passwordHash" not in data


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/auth/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_me_full_name(client: AsyncClient):
    setup = await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    access_token = setup.json()["accessToken"]
    response = await client.patch(
        "/api/auth/me",
        json={"fullName": "Updated Name"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["fullName"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_me_notifications(client: AsyncClient):
    setup = await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    access_token = setup.json()["accessToken"]
    response = await client.patch(
        "/api/auth/me",
        json={"notificationsEnabled": False},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["notificationsEnabled"] is False


@pytest.mark.asyncio
async def test_update_me_no_fields(client: AsyncClient):
    setup = await client.post("/api/auth/setup", json=ADMIN_PAYLOAD)
    access_token = setup.json()["accessToken"]
    response = await client.patch(
        "/api/auth/me",
        json={},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_me_unauthorized(client: AsyncClient):
    response = await client.patch("/api/auth/me", json={"fullName": "X"})
    assert response.status_code == 403
