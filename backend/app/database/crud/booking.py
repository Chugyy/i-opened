"""CRUD operations for booking."""

from datetime import datetime
from uuid import UUID

import asyncpg


async def create(pool: asyncpg.Pool, lead_id: UUID, calendar_id: UUID, starts_at: datetime, ends_at: datetime, gcal_event_id: str | None = None) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO bookings (lead_id, calendar_id, starts_at, ends_at, status, gcal_event_id, created_at, updated_at) VALUES ($1, $2, $3, $4, 'confirmed', $5, now(), now()) RETURNING *",
            lead_id,
            calendar_id,
            starts_at,
            ends_at,
            gcal_event_id,
        )
        return dict(row)


async def update(pool: asyncpg.Pool, booking_id: UUID, gcal_event_id: str | None = None, status: str | None = None, cancel_reason: str | None = None) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE bookings SET gcal_event_id = COALESCE($2, gcal_event_id), status = COALESCE($3, status), cancel_reason = COALESCE($4, cancel_reason), updated_at = now() WHERE id = $1 RETURNING *",
            booking_id,
            gcal_event_id,
            status,
            cancel_reason,
        )
        return dict(row) if row else None


async def is_owned_by(pool: asyncpg.Pool, booking_id: UUID | str, user_id: UUID | str) -> bool:
    """Vrai si le RDV appartient a un calendrier de cet utilisateur."""
    async with pool.acquire() as conn:
        return bool(await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM bookings b JOIN calendars c ON c.id = b.calendar_id WHERE b.id = $1::uuid AND c.user_id = $2::uuid)",
            str(booking_id),
            str(user_id),
        ))


async def list_by_calendar(pool: asyncpg.Pool, calendar_id: UUID | None, from_dt: datetime | None = None, user_id: UUID | str | None = None) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT b.* FROM bookings b JOIN calendars c ON c.id = b.calendar_id WHERE ($1::uuid IS NULL OR b.calendar_id = $1::uuid) AND ($3::uuid IS NULL OR c.user_id = $3::uuid) AND b.status = 'confirmed' AND ($2::timestamptz IS NULL OR b.starts_at >= $2) ORDER BY b.starts_at ASC",
            str(calendar_id) if calendar_id else None,
            from_dt,
            str(user_id) if user_id else None,
        )
        return [dict(r) for r in rows]


async def list_by_lead(pool: asyncpg.Pool, lead_id: UUID) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM bookings WHERE lead_id = $1 ORDER BY starts_at DESC", lead_id)
        return [dict(r) for r in rows]


async def cancel(pool: asyncpg.Pool, booking_id: UUID, reason: str | None = None) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE bookings SET status = 'cancelled', cancel_reason = $2, updated_at = now() WHERE id = $1 RETURNING *",
            booking_id,
            reason,
        )
        return dict(row) if row else None


async def list_upcoming(pool: asyncpg.Pool, calendar_id: UUID | None = None, limit: int = 10, user_id: UUID | str | None = None) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT b.*, l.first_name || ' ' || l.last_name AS lead_name, c.name AS calendar_name FROM bookings b JOIN leads l ON l.id = b.lead_id JOIN calendars c ON c.id = b.calendar_id WHERE b.status = 'confirmed' AND b.starts_at > now() AND ($1::uuid IS NULL OR b.calendar_id = $1) AND ($3::uuid IS NULL OR c.user_id = $3::uuid) ORDER BY b.starts_at ASC LIMIT $2",
            calendar_id,
            limit,
            str(user_id) if user_id else None,
        )
        return [dict(r) for r in rows]
