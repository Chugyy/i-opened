"""CRUD operations for lead."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import asyncpg


async def create(pool: asyncpg.Pool, calendar_id: UUID, first_name: str, last_name: str, email: str, phone: str, answers: list) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO leads (calendar_id, first_name, last_name, email, phone, answers, status, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6::jsonb, 'nouveau', now(), now()) RETURNING *",
            calendar_id,
            first_name,
            last_name,
            email,
            phone,
            json.dumps(answers),
        )
        return dict(row)


async def get_by_email_and_calendar(pool: asyncpg.Pool, email: str, calendar_id: UUID) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM leads WHERE email = $1 AND calendar_id = $2",
            email,
            calendar_id,
        )
        return dict(row) if row else None


async def update(pool: asyncpg.Pool, lead_id: UUID, fields: dict) -> dict | None:
    if not fields:
        return None
    processed = {}
    for k, v in fields.items():
        if k == "answers" and v is not None:
            processed[k] = json.dumps(v)
        else:
            processed[k] = v
    assignments = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(processed))
    query = f"UPDATE leads SET {assignments}, updated_at = now() WHERE id = $1 RETURNING *"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, lead_id, *processed.values())
        return dict(row) if row else None


async def list(pool: asyncpg.Pool, calendar_id: UUID | None = None, status: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    conditions = ["TRUE"]
    params: list = []
    idx = 1

    if calendar_id is not None:
        conditions.append(f"l.calendar_id = ${idx}")
        params.append(calendar_id)
        idx += 1
    if status is not None:
        conditions.append(f"l.status = ${idx}")
        params.append(status)
        idx += 1
    if date_from is not None:
        conditions.append(f"l.created_at >= ${idx}")
        params.append(date_from)
        idx += 1
    if date_to is not None:
        conditions.append(f"l.created_at <= ${idx}")
        params.append(date_to)
        idx += 1

    conditions_sql = " AND ".join(conditions)
    params.append(limit)
    params.append(offset)
    query = f"SELECT l.id, l.calendar_id, c.name AS calendar_name, l.first_name, l.last_name, l.email, l.phone, l.status, l.created_at FROM leads l LEFT JOIN calendars c ON c.id = l.calendar_id WHERE {conditions_sql} ORDER BY l.created_at DESC LIMIT ${idx} OFFSET ${idx + 1}"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


async def count_by_status(pool: asyncpg.Pool, calendar_id: UUID | None = None) -> list[dict]:
    if calendar_id is not None:
        query = "SELECT status, COUNT(*) as count FROM leads WHERE calendar_id = $1 GROUP BY status"
        params = [calendar_id]
    else:
        query = "SELECT status, COUNT(*) as count FROM leads GROUP BY status"
        params = []

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


async def delete(pool: asyncpg.Pool, lead_id: UUID) -> None:
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM leads WHERE id = $1", lead_id)


async def get_detail(pool: asyncpg.Pool, lead_id: UUID) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT l.*, c.name AS calendar_name FROM leads l LEFT JOIN calendars c ON c.id = l.calendar_id WHERE l.id = $1",
            lead_id,
        )
        return dict(row) if row else None
