"""CRUD operations for availability."""

from datetime import time
from uuid import UUID

import asyncpg


def _parse_time(value) -> time:
    """Convert string 'HH:MM' or time object to time."""
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        parts = value.split(":")
        return time(int(parts[0]), int(parts[1]))
    return value


async def upsert_by_calendar(pool: asyncpg.Pool, calendar_id: str | UUID, availabilities: list[dict]) -> list[dict]:
    """Delete existing + insert new availabilities for a calendar. Returns all rows."""
    cal_id = UUID(str(calendar_id))
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM availabilities WHERE calendar_id = $1", cal_id)
            rows = []
            for a in availabilities:
                row = await conn.fetchrow(
                    """INSERT INTO availabilities (calendar_id, day_of_week, start_time, end_time, lunch_start, lunch_end, is_active, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, now(), now())
                    RETURNING *""",
                    cal_id,
                    a["day_of_week"],
                    _parse_time(a["start_time"]),
                    _parse_time(a["end_time"]),
                    _parse_time(a["lunch_start"]) if a.get("lunch_start") else None,
                    _parse_time(a["lunch_end"]) if a.get("lunch_end") else None,
                    a["is_active"],
                )
                rows.append(dict(row))
            return rows


async def list_by_calendar(pool: asyncpg.Pool, calendar_id: str | UUID) -> list[dict]:
    cal_id = UUID(str(calendar_id))
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM availabilities WHERE calendar_id = $1 ORDER BY day_of_week ASC", cal_id)
        return [dict(r) for r in rows]
