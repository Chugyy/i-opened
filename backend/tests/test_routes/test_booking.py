"""Endpoint tests for booking routes — admin + public flow."""

import pytest
import asyncpg
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from config.config import settings


# ---------------------------------------------------------------------------
# App + client fixture
# ---------------------------------------------------------------------------

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
    await p.close()


@pytest.fixture
async def app(pool):
    from fastapi import FastAPI
    from app.api.routes.booking import router as booking_router
    from app.api.routes.book import router as book_router

    application = FastAPI()
    application.state.pool = pool
    application.include_router(booking_router)
    application.include_router(book_router)
    return application


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def _auth_headers():
    """Generate a valid JWT for tests."""
    from app.core.utils.user import generate_tokens
    tokens = generate_tokens(user_id="00000000-0000-0000-0000-000000000001", email="admin@test.com")
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---------------------------------------------------------------------------
# Admin — GET /api/bookings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_bookings_unauthorized(client):
    response = await client.get("/api/bookings")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_bookings_empty(client):
    with patch("app.api.routes.booking.booking_crud.list_by_calendar", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/api/bookings", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_list_bookings_invalid_status(client):
    response = await client.get("/api/bookings?status=invalid", headers=_auth_headers())
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_bookings_invalid_date(client):
    response = await client.get("/api/bookings?dateFrom=not-a-date", headers=_auth_headers())
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Admin — GET /api/bookings/upcoming
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_upcoming_unauthorized(client):
    response = await client.get("/api/bookings/upcoming")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_upcoming_empty(client):
    with patch("app.api.routes.booking.booking_crud.list_upcoming", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/api/bookings/upcoming", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert isinstance(data["data"], list)


# ---------------------------------------------------------------------------
# Admin — PATCH /api/bookings/{id}/cancel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_booking_not_found(client):
    with patch("app.api.routes.booking.booking_crud.cancel", new_callable=AsyncMock, return_value=None), \
         patch("app.api.routes.booking.booking_crud.list_by_lead", new_callable=AsyncMock, return_value=[]):
        response = await client.patch(
            "/api/bookings/00000000-0000-0000-0000-000000000099/cancel",
            json={},
            headers=_auth_headers(),
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_booking_unauthorized(client):
    response = await client.patch("/api/bookings/some-id/cancel", json={})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Admin — PATCH /api/bookings/{id}/no-show
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_show_not_found(client):
    with patch("app.api.routes.booking.booking_crud.update", new_callable=AsyncMock, return_value=None):
        response = await client.patch(
            "/api/bookings/00000000-0000-0000-0000-000000000099/no-show",
            headers=_auth_headers(),
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_no_show_unauthorized(client):
    response = await client.patch("/api/bookings/some-id/no-show")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Public — GET /api/book/{slug}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_public_calendar_not_found(client):
    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value=None):
        response = await client.get("/api/book/nonexistent-slug")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_public_calendar_inactive(client):
    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value={
        "id": "cal-id", "name": "Test", "status": "inactive", "slot_duration": 30, "description": None
    }):
        response = await client.get("/api/book/inactive-slug")
    assert response.status_code == 410


@pytest.mark.asyncio
async def test_get_public_calendar_ok(client):
    mock_calendar = {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "Consultation",
        "status": "active",
        "slot_duration": 30,
        "description": "Test calendar",
    }
    mock_questions = [
        {"id": "q1", "label": "Budget?", "type": "number", "options": None, "position": 1, "required": True}
    ]
    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value=mock_calendar), \
         patch("app.api.routes.book.question_crud.list_by_calendar", new_callable=AsyncMock, return_value=mock_questions):
        response = await client.get("/api/book/consultation")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Consultation"
    assert data["slotDuration"] == 30
    assert len(data["questions"]) == 1


# ---------------------------------------------------------------------------
# Public — POST /api/book/{slug}/qualify
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_qualify_not_found(client):
    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value=None):
        response = await client.post("/api/book/nonexistent/qualify", json={
            "firstName": "Jean", "lastName": "Dupont",
            "email": "jean@test.com", "phone": "+33612345678", "answers": []
        })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_qualify_validation_error_phone(client):
    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value={
        "id": "cal-id", "status": "active", "slot_duration": 30
    }):
        response = await client.post("/api/book/slug/qualify", json={
            "firstName": "Jean", "lastName": "Dupont",
            "email": "jean@test.com", "phone": "invalid-phone", "answers": []
        })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_qualify_new_lead_qualified(client):
    mock_calendar = {"id": "cal-uuid", "status": "active", "slot_duration": 30}
    mock_lead = {"id": "lead-uuid", "status": "qualifie", "email": "jean@test.com"}

    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value=mock_calendar), \
         patch("app.api.routes.book.question_crud.list_by_calendar", new_callable=AsyncMock, return_value=[]), \
         patch("app.api.routes.book.lead_crud.get_by_email_and_calendar", new_callable=AsyncMock, return_value=None), \
         patch("app.api.routes.book.lead_crud.create", new_callable=AsyncMock, return_value=mock_lead), \
         patch("app.api.routes.book.rule_crud.list_by_calendar", new_callable=AsyncMock, return_value=[]), \
         patch("app.api.routes.book.lead_crud.update", new_callable=AsyncMock, return_value=mock_lead):
        response = await client.post("/api/book/consultation/qualify", json={
            "firstName": "Jean", "lastName": "Dupont",
            "email": "jean@test.com", "phone": "+33612345678", "answers": []
        })
    assert response.status_code == 200
    data = response.json()
    assert data["qualified"] is True
    assert data["isNew"] is True
    assert "leadId" in data


# ---------------------------------------------------------------------------
# Public — GET /api/book/{slug}/slots
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_slots_missing_date(client):
    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value={
        "id": "cal-id", "status": "active", "slot_duration": 30
    }):
        response = await client.get("/api/book/slug/slots?leadId=lead-uuid")
    assert response.status_code == 422  # missing required date param


@pytest.mark.asyncio
async def test_get_slots_lead_not_qualified(client):
    mock_calendar = {"id": "cal-uuid", "status": "active", "slot_duration": 30}
    mock_lead = {"id": "lead-uuid", "status": "non_qualifie"}

    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value=mock_calendar), \
         patch("app.api.routes.book.lead_crud.get_detail", new_callable=AsyncMock, return_value=mock_lead), \
         patch("app.api.routes.book.lead_crud.list", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/api/book/slug/slots?date=2026-05-01&leadId=lead-uuid")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_slots_no_availability(client):
    mock_calendar = {"id": "cal-uuid", "status": "active", "slot_duration": 30}
    mock_lead = {"id": "lead-uuid", "status": "qualifie"}

    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value=mock_calendar), \
         patch("app.api.routes.book.lead_crud.get_detail", new_callable=AsyncMock, return_value=mock_lead), \
         patch("app.api.routes.book.lead_crud.list", new_callable=AsyncMock, return_value=[]), \
         patch("app.api.routes.book.availability_crud.list_by_calendar", new_callable=AsyncMock, return_value=[]):
        response = await client.get("/api/book/slug/slots?date=2026-05-01&leadId=lead-uuid")
    assert response.status_code == 200
    data = response.json()
    assert data["slots"] == []


# ---------------------------------------------------------------------------
# Public — POST /api/book/{slug}/confirm
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_confirm_booking_calendar_not_found(client):
    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value=None):
        response = await client.post("/api/book/bad-slug/confirm", json={
            "leadId": "lead-uuid", "startsAt": "2026-05-01T10:00:00+00:00"
        })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_confirm_booking_lead_not_qualified(client):
    mock_calendar = {"id": "cal-uuid", "status": "active", "slot_duration": 30}
    mock_lead = {"id": "lead-uuid", "status": "non_qualifie"}

    with patch("app.api.routes.book.calendar_crud.get_by_slug", new_callable=AsyncMock, return_value=mock_calendar), \
         patch("app.api.routes.book.lead_crud.get_detail", new_callable=AsyncMock, return_value=mock_lead), \
         patch("app.api.routes.book.lead_crud.list", new_callable=AsyncMock, return_value=[]):
        response = await client.post("/api/book/slug/confirm", json={
            "leadId": "lead-uuid", "startsAt": "2026-05-01T10:00:00+00:00"
        })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_confirm_booking_validation_error(client):
    response = await client.post("/api/book/slug/confirm", json={})
    assert response.status_code == 422
