"""CRUD operations for calendar."""

from __future__ import annotations

from uuid import UUID

import asyncpg


async def create(pool: asyncpg.Pool, id: UUID, user_id: UUID, name: str, slug: str, description: str | None, slot_duration: int) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO calendars (id, user_id, name, slug, description, slot_duration, status, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, 'incomplete', now(), now()) RETURNING *",
            id,
            user_id,
            name,
            slug,
            description,
            slot_duration,
        )
        return dict(row)


async def get(pool: asyncpg.Pool, calendar_id: UUID) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM calendars WHERE id = $1", calendar_id)
        return dict(row) if row else None


async def get_by_slug(pool: asyncpg.Pool, slug: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM calendars WHERE slug = $1", slug)
        return dict(row) if row else None


async def update(pool: asyncpg.Pool, calendar_id: UUID, fields: dict) -> dict | None:
    if not fields:
        return None
    assignments = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(fields))
    query = f"UPDATE calendars SET {assignments}, updated_at = now() WHERE id = $1 RETURNING *"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, calendar_id, *fields.values())
        return dict(row) if row else None


async def delete(pool: asyncpg.Pool, calendar_id: UUID) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM calendars WHERE id = $1 RETURNING id",
            calendar_id,
        )
        return row is not None


async def list(pool: asyncpg.Pool, user_id: UUID) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM calendars WHERE user_id = $1 ORDER BY created_at DESC", user_id)
        return [dict(r) for r in rows]
