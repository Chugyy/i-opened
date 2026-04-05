"""CRUD operations for automation."""

from __future__ import annotations

from uuid import UUID

import asyncpg


async def create(pool: asyncpg.Pool, id: UUID, user_id: UUID, calendar_id: UUID | None, name: str, trigger: str, is_active: bool) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO automations (id, user_id, calendar_id, name, trigger, is_active, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, now(), now()) RETURNING *",
            id,
            user_id,
            calendar_id,
            name,
            trigger,
            is_active,
        )
        return dict(row)


async def get(pool: asyncpg.Pool, automation_id: UUID) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM automations WHERE id = $1", automation_id)
        return dict(row) if row else None


async def update(pool: asyncpg.Pool, automation_id: UUID, fields: dict) -> dict | None:
    if not fields:
        return None
    assignments = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(fields))
    query = f"UPDATE automations SET {assignments}, updated_at = now() WHERE id = $1 RETURNING *"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, automation_id, *fields.values())
        return dict(row) if row else None


async def delete(pool: asyncpg.Pool, automation_id: UUID) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM automations WHERE id = $1 RETURNING id",
            automation_id,
        )
        return row is not None


async def list(pool: asyncpg.Pool, user_id: UUID | None = None, calendar_id: UUID | str | None = None, trigger: str | None = None) -> list[dict]:
    conditions = []
    params: list = []
    idx = 1

    if user_id is not None:
        conditions.append(f"user_id = ${idx}")
        params.append(user_id if isinstance(user_id, UUID) else UUID(str(user_id)))
        idx += 1
    if calendar_id is not None:
        conditions.append(f"(calendar_id = ${idx} OR calendar_id IS NULL)")
        params.append(calendar_id if isinstance(calendar_id, UUID) else UUID(str(calendar_id)))
        idx += 1
    if trigger is not None:
        conditions.append(f"trigger = ${idx}")
        params.append(trigger)
        idx += 1

    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM automations{where} ORDER BY created_at DESC"
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


async def toggle_active(pool: asyncpg.Pool, automation_id: UUID, is_active: bool) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE automations SET is_active = $2, updated_at = now() WHERE id = $1 RETURNING *",
            automation_id,
            is_active,
        )
        return dict(row) if row else None


async def disable_by_calendar(pool: asyncpg.Pool, calendar_id: UUID) -> int:
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE automations SET is_active = false, updated_at = now() WHERE calendar_id = $1 AND is_active = true",
            calendar_id,
        )
        # asyncpg execute returns "UPDATE N"
        return int(result.split()[-1])
