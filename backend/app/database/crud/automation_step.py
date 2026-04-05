"""CRUD operations for automation_step."""

from uuid import UUID

import asyncpg


async def get(pool: asyncpg.Pool, step_id: UUID) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM automation_steps WHERE id = $1", step_id)
        return dict(row) if row else None


async def create(pool: asyncpg.Pool, automation_id: UUID, channel: str, delay_value: int, delay_unit: str, content: str, position: int) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO automation_steps (automation_id, channel, delay_value, delay_unit, content, position, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, now(), now()) RETURNING *",
            automation_id,
            channel,
            delay_value,
            delay_unit,
            content,
            position,
        )
        return dict(row)


async def update(pool: asyncpg.Pool, step_id: UUID, fields: dict) -> dict | None:
    if not fields:
        return None
    assignments = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(fields))
    query = f"UPDATE automation_steps SET {assignments}, updated_at = now() WHERE id = $1 RETURNING *"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, step_id, *fields.values())
        return dict(row) if row else None


async def delete(pool: asyncpg.Pool, step_id: UUID) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM automation_steps WHERE id = $1 RETURNING id",
            step_id,
        )
        return row is not None


async def list_by_automation(pool: asyncpg.Pool, automation_id: UUID) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM automation_steps WHERE automation_id = $1 ORDER BY position ASC", automation_id)
        return [dict(r) for r in rows]


async def reorder(pool: asyncpg.Pool, automation_id: UUID, ordered_ids: list[UUID]) -> list[dict]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            for position, sid in enumerate(ordered_ids):
                await conn.execute(
                    "UPDATE automation_steps SET position = $1, updated_at = now() WHERE id = $2 AND automation_id = $3",
                    position,
                    sid,
                    automation_id,
                )
        rows = await conn.fetch("SELECT * FROM automation_steps WHERE automation_id = $1 ORDER BY position ASC", automation_id)
        return [dict(r) for r in rows]
