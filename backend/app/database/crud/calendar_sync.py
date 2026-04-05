"""CRUD operations for calendar_sync."""

from datetime import datetime
from uuid import UUID

import asyncpg


async def create(pool: asyncpg.Pool, id: UUID, calendar_id: UUID, access_token: str, refresh_token: str, token_expiry: datetime, sync_token: str | None = None) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO calendar_syncs (id, calendar_id, access_token, refresh_token, token_expiry, sync_token, status, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, 'connected', now(), now()) RETURNING *",
            id,
            calendar_id,
            access_token,
            refresh_token,
            token_expiry,
            sync_token,
        )
        return dict(row)


async def get_by_calendar(pool: asyncpg.Pool, calendar_id: UUID) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM calendar_syncs WHERE calendar_id = $1", calendar_id)
        return dict(row) if row else None


async def update(pool: asyncpg.Pool, calendar_id: UUID, fields: dict) -> dict | None:
    if not fields:
        return None
    assignments = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(fields))
    query = f"UPDATE calendar_syncs SET {assignments}, updated_at = now() WHERE calendar_id = $1 RETURNING *"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, calendar_id, *fields.values())
        return dict(row) if row else None


async def delete(pool: asyncpg.Pool, calendar_id: UUID) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM calendar_syncs WHERE calendar_id = $1 RETURNING calendar_id",
            calendar_id,
        )
        return row is not None
