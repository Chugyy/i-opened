"""Failles bloquantes avant un second client : /auth/setup ouvert, donnees non cloisonnees.

Chaque test pose ses propres donnees (utilisateurs, calendriers, leads, RDV) et les retire
ensuite ; la base cible est celle de la config de test (jamais la prod).
"""

import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.core.utils.user import generate_tokens
from app.database.crud import booking as booking_crud
from app.database.crud import calendar as calendar_crud
from app.database.crud import lead as lead_crud
from app.database.crud import user as user_crud
from config.config import settings

pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(
        host=settings.db_host, port=settings.db_port, database=settings.db_name,
        user=settings.db_user, password=settings.db_password or "", min_size=1, max_size=3,
    )
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM users")
    yield p
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM users")
    await p.close()


@pytest_asyncio.fixture
async def client(pool):
    app.state.pool = pool
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _owner(pool, tag: str) -> dict:
    """Utilisateur + calendrier actif + lead + RDV a venir ; renvoie ids et en-tete d'auth."""
    user = await user_crud.create(pool, email=f"{tag}@test.com", full_name=tag, password_hash="x")
    cal = await calendar_crud.create(
        pool, id=uuid.uuid4(), user_id=user["id"], name=f"Cal {tag}",
        slug=f"cal-{tag}", description=None, slot_duration=30,
    )
    await calendar_crud.update(pool, calendar_id=cal["id"], fields={"status": "active"})
    lead = await lead_crud.create(
        pool, calendar_id=cal["id"], first_name=tag, last_name="Lead",
        email=f"lead-{tag}@x.com", phone="+33600000000", answers=[],
    )
    start = datetime.now(timezone.utc) + timedelta(days=2)
    booking = await booking_crud.create(
        pool, lead_id=lead["id"], calendar_id=cal["id"],
        starts_at=start, ends_at=start + timedelta(minutes=30),
    )
    token = generate_tokens(user_id=user["id"], email=user["email"])["access_token"]
    return {
        "user": user, "cal": cal, "lead": lead, "booking": booking,
        "h": {"Authorization": f"Bearer {token}"},
    }


# --------------------------- Faille 1 : /auth/setup ouvert ---------------------------

async def test_setup_refused_when_admin_exists(client):
    first = await client.post("/api/auth/setup", json={
        "email": "admin@test.com", "password": "securepass123", "fullName": "Admin"})
    assert first.status_code == 201
    second = await client.post("/api/auth/setup", json={
        "email": "intrus@evil.com", "password": "securepass123", "fullName": "Intrus"})
    assert second.status_code in (403, 409)


async def test_setup_requires_install_secret_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "setup_secret", "s3cret-install", raising=False)
    payload = {"email": "admin@test.com", "password": "securepass123", "fullName": "Admin"}
    assert (await client.post("/api/auth/setup", json=payload)).status_code == 403
    bad = await client.post("/api/auth/setup", json=payload, headers={"X-Setup-Secret": "nope"})
    assert bad.status_code == 403
    ok = await client.post("/api/auth/setup", json=payload, headers={"X-Setup-Secret": "s3cret-install"})
    assert ok.status_code == 201


# --------------------------- Faille 2 : leads non cloisonnes ---------------------------

async def test_leads_list_scoped_to_owner(client, pool):
    a, b = await _owner(pool, "alice"), await _owner(pool, "bob")
    r = await client.get("/api/leads", headers=a["h"])
    assert r.status_code == 200
    emails = {x["email"] for x in r.json()["data"]}
    assert emails == {"lead-alice@x.com"}


async def test_leads_filter_on_foreign_calendar_is_empty(client, pool):
    a, b = await _owner(pool, "alice"), await _owner(pool, "bob")
    r = await client.get("/api/leads", params={"calendar_id": str(b["cal"]["id"])}, headers=a["h"])
    assert r.json()["data"] == []


async def test_lead_stats_scoped_to_owner(client, pool):
    a, b = await _owner(pool, "alice"), await _owner(pool, "bob")
    r = await client.get("/api/leads/stats", headers=a["h"])
    assert r.json()["nouveau"] == 1


async def test_foreign_lead_detail_status_delete_are_404(client, pool):
    a, b = await _owner(pool, "alice"), await _owner(pool, "bob")
    lid = str(b["lead"]["id"])
    assert (await client.get(f"/api/leads/{lid}", headers=a["h"])).status_code == 404
    assert (await client.patch(f"/api/leads/{lid}/status", json={"status": "qualifie"}, headers=a["h"])).status_code == 404
    assert (await client.delete(f"/api/leads/{lid}", headers=a["h"])).status_code == 404
    assert (await client.get(f"/api/leads/{lid}", headers=b["h"])).status_code == 200


async def test_bookings_scoped_to_owner(client, pool):
    a, b = await _owner(pool, "alice"), await _owner(pool, "bob")
    r = await client.get("/api/bookings/upcoming", headers=a["h"])
    assert {x["leadId"] for x in r.json()["data"]} == {str(a["lead"]["id"])}
    bid = str(b["booking"]["id"])
    assert (await client.patch(f"/api/bookings/{bid}/cancel", json={"reason": "x"}, headers=a["h"])).status_code == 404
    assert (await client.patch(f"/api/bookings/{bid}/no-show", headers=a["h"])).status_code == 404


async def test_dashboard_scoped_to_owner(client, pool):
    a, b = await _owner(pool, "alice"), await _owner(pool, "bob")
    r = await client.get("/api/dashboard", headers=a["h"])
    assert r.json()["leadsThisWeek"] == 1 or r.json().get("leads_this_week") == 1


async def test_foreign_calendar_is_404(client, pool):
    a, b = await _owner(pool, "alice"), await _owner(pool, "bob")
    cid = str(b["cal"]["id"])
    for path in ("", "/availabilities", "/questions", "/rules"):
        assert (await client.get(f"/api/calendars/{cid}{path}", headers=a["h"])).status_code == 404, path
    assert (await client.delete(f"/api/calendars/{cid}", headers=a["h"])).status_code == 404
    assert (await client.get(f"/api/calendars/{cid}", headers=b["h"])).status_code == 200


# --------------------------- Non-regression : flux public ---------------------------

async def test_public_booking_page_still_open(client, pool):
    await _owner(pool, "alice")
    r = await client.get("/api/book/cal-alice")   # sans token
    assert r.status_code == 200
    assert r.json().get("name") == "Cal alice" or r.json().get("calendarId")
