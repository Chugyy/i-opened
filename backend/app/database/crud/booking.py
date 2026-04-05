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


async def list_by_calendar(pool: asyncpg.Pool, calendar_id: UUID, from_dt: datetime | None = None) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM bookings WHERE calendar_id = $1 AND status = 'confirmed' AND ($2::timestamptz IS NULL OR starts_at >= $2) ORDER BY starts_at ASC",
            calendar_id,
            from_dt,
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


async def list_upcoming(pool: asyncpg.Pool, calendar_id: UUID | None = None, limit: int = 10) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT b.*, l.first_name || ' ' || l.last_name AS lead_name, c.name AS calendar_name FROM bookings b JOIN leads l ON l.id = b.lead_id JOIN calendars c ON c.id = b.calendar_id WHERE b.status = 'confirmed' AND b.starts_at > now() AND ($1::uuid IS NULL OR b.calendar_id = $1) ORDER BY b.starts_at ASC LIMIT $2",
            calendar_id,
            limit,
        )
        return [dict(r) for r in rows]
