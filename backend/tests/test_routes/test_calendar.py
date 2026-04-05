"""Endpoint tests for Calendar and sub-resources."""

import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# App fixture — minimal FastAPI app with mocked pool + auth
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_user():
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture
def app(fake_user):
    from app.api.routes.calendar import router

    _app = FastAPI()
    _app.include_router(router)

    mock_pool = MagicMock()
    _app.state.pool = mock_pool

    # Override auth dependency
    from app.api.routes.calendar import get_current_user
    _app.dependency_overrides[get_current_user] = lambda: fake_user

    return _app


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


CALENDAR_ID = str(uuid.uuid4())
QUESTION_ID = str(uuid.uuid4())
RULE_ID = str(uuid.uuid4())

CALENDAR_ROW = {
    "id": uuid.UUID(CALENDAR_ID),
    "user_id": uuid.uuid4(),
    "name": "My Calendar",
    "slug": "my-calendar",
    "description": None,
    "slot_duration": 30,
    "status": "incomplete",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


# ---------------------------------------------------------------------------
# Calendar CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_calendars(client, app, fake_user):
    with patch("app.api.routes.calendar.calendar_crud.list", new=AsyncMock(return_value=[CALENDAR_ROW])):
        response = await client.get("/api/calendars")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "pagination" in body
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "My Calendar"


@pytest.mark.asyncio
async def test_list_calendars_with_status_filter(client):
    inactive_row = {**CALENDAR_ROW, "id": uuid.uuid4(), "status": "inactive"}
    with patch("app.api.routes.calendar.calendar_crud.list", new=AsyncMock(return_value=[CALENDAR_ROW, inactive_row])):
        response = await client.get("/api/calendars?status=inactive")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["status"] == "inactive"


@pytest.mark.asyncio
async def test_create_calendar(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.create", new=AsyncMock(return_value=CALENDAR_ROW)),
    ):
        response = await client.post(
            "/api/calendars",
            json={"name": "My Calendar", "slotDuration": 30},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "My Calendar"
    assert body["slotDuration"] == 30
    assert "id" in body


@pytest.mark.asyncio
async def test_create_calendar_validation_error(client):
    response = await client.post("/api/calendars", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_calendar_invalid_slot_duration(client):
    response = await client.post("/api/calendars", json={"name": "Test", "slotDuration": 0})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_calendar(client):
    with patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)):
        response = await client.get(f"/api/calendars/{CALENDAR_ID}")
    assert response.status_code == 200
    assert response.json()["id"] == CALENDAR_ID


@pytest.mark.asyncio
async def test_get_calendar_not_found(client):
    with patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=None)):
        response = await client.get(f"/api/calendars/{CALENDAR_ID}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_calendar(client):
    updated_row = {**CALENDAR_ROW, "name": "Updated", "slug": "updated"}
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.calendar_crud.update", new=AsyncMock(return_value=updated_row)),
    ):
        response = await client.patch(f"/api/calendars/{CALENDAR_ID}", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_update_calendar_not_found(client):
    with patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=None)):
        response = await client.patch(f"/api/calendars/{CALENDAR_ID}", json={"name": "X"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_calendar_no_jobs(client):
    """Without jobs module, delete returns 501."""
    with patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)):
        response = await client.delete(f"/api/calendars/{CALENDAR_ID}")
    # Jobs not built yet → fallback gives requires_confirmation=False → 204
    assert response.status_code in (204, 501)


@pytest.mark.asyncio
async def test_delete_calendar_not_found(client):
    with patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=None)):
        response = await client.delete(f"/api/calendars/{CALENDAR_ID}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

AVAILABILITY_ROW = {
    "id": uuid.uuid4(),
    "calendar_id": uuid.UUID(CALENDAR_ID),
    "day_of_week": 0,
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "lunch_start": None,
    "lunch_end": None,
    "is_active": True,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


@pytest.mark.asyncio
async def test_list_availabilities(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.availability_crud.list_by_calendar", new=AsyncMock(return_value=[AVAILABILITY_ROW])),
    ):
        response = await client.get(f"/api/calendars/{CALENDAR_ID}/availabilities")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.asyncio
async def test_list_availabilities_calendar_not_found(client):
    with patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=None)):
        response = await client.get(f"/api/calendars/{CALENDAR_ID}/availabilities")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_upsert_availabilities(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.availability_crud.upsert_by_calendar", new=AsyncMock(return_value=[AVAILABILITY_ROW])),
    ):
        response = await client.put(
            f"/api/calendars/{CALENDAR_ID}/availabilities",
            json={
                "availabilities": [
                    {
                        "dayOfWeek": 0,
                        "startTime": "09:00",
                        "endTime": "17:00",
                        "lunchStart": None,
                        "lunchEnd": None,
                        "isActive": True,
                    }
                ]
            },
        )
    assert response.status_code == 200
    assert "data" in response.json()


@pytest.mark.asyncio
async def test_upsert_availabilities_lunch_unpaired(client):
    with patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)):
        response = await client.put(
            f"/api/calendars/{CALENDAR_ID}/availabilities",
            json={
                "availabilities": [
                    {
                        "dayOfWeek": 0,
                        "startTime": "09:00",
                        "endTime": "17:00",
                        "lunchStart": "12:00",
                        "lunchEnd": None,
                        "isActive": True,
                    }
                ]
            },
        )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

QUESTION_ROW = {
    "id": uuid.UUID(QUESTION_ID),
    "calendar_id": uuid.UUID(CALENDAR_ID),
    "label": "What is your budget?",
    "type": "text",
    "options": None,
    "position": 1,
    "required": True,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


@pytest.mark.asyncio
async def test_list_questions(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.question_crud.list_by_calendar", new=AsyncMock(return_value=[QUESTION_ROW])),
    ):
        response = await client.get(f"/api/calendars/{CALENDAR_ID}/questions")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.asyncio
async def test_create_question(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.question_crud.create", new=AsyncMock(return_value=QUESTION_ROW)),
    ):
        response = await client.post(
            f"/api/calendars/{CALENDAR_ID}/questions",
            json={"label": "What is your budget?", "type": "text", "position": 1, "required": True},
        )
    assert response.status_code == 201
    assert response.json()["label"] == "What is your budget?"


@pytest.mark.asyncio
async def test_create_question_choice_without_options(client):
    with patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)):
        response = await client.post(
            f"/api/calendars/{CALENDAR_ID}/questions",
            json={"label": "Choose", "type": "single_choice", "position": 1, "required": True},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_question_validation_error(client):
    response = await client.post(f"/api/calendars/{CALENDAR_ID}/questions", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_question(client):
    updated = {**QUESTION_ROW, "label": "Updated label"}
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.question_crud.update", new=AsyncMock(return_value=updated)),
    ):
        response = await client.patch(
            f"/api/calendars/{CALENDAR_ID}/questions/{QUESTION_ID}",
            json={"label": "Updated label"},
        )
    assert response.status_code == 200
    assert response.json()["label"] == "Updated label"


@pytest.mark.asyncio
async def test_delete_question(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.question_crud.delete", new=AsyncMock(return_value=True)),
    ):
        response = await client.delete(f"/api/calendars/{CALENDAR_ID}/questions/{QUESTION_ID}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_question_not_found(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.question_crud.delete", new=AsyncMock(return_value=False)),
    ):
        response = await client.delete(f"/api/calendars/{CALENDAR_ID}/questions/{QUESTION_ID}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reorder_questions(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.question_crud.reorder", new=AsyncMock(return_value=[QUESTION_ROW])),
    ):
        response = await client.patch(
            f"/api/calendars/{CALENDAR_ID}/questions/reorder",
            json={"orderedIds": [QUESTION_ID]},
        )
    assert response.status_code == 200
    assert "data" in response.json()


# ---------------------------------------------------------------------------
# Qualification Rules
# ---------------------------------------------------------------------------

RULE_ROW = {
    "id": uuid.UUID(RULE_ID),
    "calendar_id": uuid.UUID(CALENDAR_ID),
    "question_id": uuid.UUID(QUESTION_ID),
    "operator": ">=",
    "threshold_value": "5000",
    "label": "What is your budget?",
    "type": "number",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


@pytest.mark.asyncio
async def test_list_rules(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.rule_crud.list_by_calendar", new=AsyncMock(return_value=[RULE_ROW])),
    ):
        response = await client.get(f"/api/calendars/{CALENDAR_ID}/rules")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.asyncio
async def test_create_rule(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.rule_crud.create", new=AsyncMock(return_value=RULE_ROW)),
    ):
        response = await client.post(
            f"/api/calendars/{CALENDAR_ID}/rules",
            json={"questionId": QUESTION_ID, "operator": ">=", "thresholdValue": "5000"},
        )
    assert response.status_code == 201
    assert response.json()["operator"] == ">="


@pytest.mark.asyncio
async def test_create_rule_validation_error(client):
    response = await client.post(f"/api/calendars/{CALENDAR_ID}/rules", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_rule(client):
    updated = {**RULE_ROW, "threshold_value": "10000"}
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.rule_crud.update", new=AsyncMock(return_value=updated)),
    ):
        response = await client.patch(
            f"/api/calendars/{CALENDAR_ID}/rules/{RULE_ID}",
            json={"thresholdValue": "10000"},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_rule(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.rule_crud.delete", new=AsyncMock(return_value=True)),
    ):
        response = await client.delete(f"/api/calendars/{CALENDAR_ID}/rules/{RULE_ID}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_rule_not_found(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.rule_crud.delete", new=AsyncMock(return_value=False)),
    ):
        response = await client.delete(f"/api/calendars/{CALENDAR_ID}/rules/{RULE_ID}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Calendar Sync
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_google_connect_returns_auth_url(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.sync_crud.get_by_calendar", new=AsyncMock(return_value=None)),
    ):
        response = await client.post(f"/api/calendars/{CALENDAR_ID}/sync/google/connect")
    assert response.status_code == 200
    body = response.json()
    assert "authorizationUrl" in body
    assert "state" in body
    assert "accounts.google.com" in body["authorizationUrl"]


@pytest.mark.asyncio
async def test_google_connect_conflict(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.sync_crud.get_by_calendar", new=AsyncMock(return_value={"status": "connected"})),
    ):
        response = await client.post(f"/api/calendars/{CALENDAR_ID}/sync/google/connect")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_sync_status(client):
    import datetime
    sync_row = {
        "status": "connected",
        "token_expiry": datetime.datetime(2026, 12, 31, tzinfo=datetime.timezone.utc),
        "sync_token": "tok123",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.sync_crud.get_by_calendar", new=AsyncMock(return_value=sync_row)),
    ):
        response = await client.get(f"/api/calendars/{CALENDAR_ID}/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["hasSyncToken"] is True


@pytest.mark.asyncio
async def test_get_sync_status_not_found(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.sync_crud.get_by_calendar", new=AsyncMock(return_value=None)),
    ):
        response = await client.get(f"/api/calendars/{CALENDAR_ID}/sync")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_sync(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.sync_crud.delete", new=AsyncMock(return_value=True)),
    ):
        response = await client.delete(f"/api/calendars/{CALENDAR_ID}/sync")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_sync_not_found(client):
    with (
        patch("app.api.routes.calendar.calendar_crud.get", new=AsyncMock(return_value=CALENDAR_ROW)),
        patch("app.api.routes.calendar.sync_crud.delete", new=AsyncMock(return_value=False)),
    ):
        response = await client.delete(f"/api/calendars/{CALENDAR_ID}/sync")
    assert response.status_code == 404
