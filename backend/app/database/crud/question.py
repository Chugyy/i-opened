"""CRUD operations for question."""

import json
from uuid import UUID

import asyncpg


async def create(pool: asyncpg.Pool, calendar_id: UUID, label: str, type: str, options: list | None, position: int, required: bool) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO questions (calendar_id, label, type, options, position, required, created_at, updated_at) VALUES ($1, $2, $3, $4::jsonb, $5, $6, now(), now()) RETURNING *",
            calendar_id,
            label,
            type,
            json.dumps(options) if options is not None else None,
            position,
            required,
        )
        return dict(row)


async def update(pool: asyncpg.Pool, question_id: UUID, fields: dict) -> dict | None:
    if not fields:
        return None
    processed = {}
    for k, v in fields.items():
        if k == "options" and v is not None:
            processed[k] = json.dumps(v)
        else:
            processed[k] = v
    assignments = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(processed))
    query = f"UPDATE questions SET {assignments}, updated_at = now() WHERE id = $1 RETURNING *"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, question_id, *processed.values())
        return dict(row) if row else None


async def delete(pool: asyncpg.Pool, question_id: UUID) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM questions WHERE id = $1 RETURNING id",
            question_id,
        )
        return row is not None


async def list_by_calendar(pool: asyncpg.Pool, calendar_id: UUID) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM questions WHERE calendar_id = $1 ORDER BY position ASC", calendar_id)
        return [dict(r) for r in rows]


async def reorder(pool: asyncpg.Pool, calendar_id: UUID, ordered_ids: list[UUID]) -> list[dict]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            for position, qid in enumerate(ordered_ids, start=1):
                await conn.execute(
                    "UPDATE questions SET position = $1, updated_at = now() WHERE id = $2 AND calendar_id = $3",
                    position,
                    qid,
                    calendar_id,
                )
        rows = await conn.fetch("SELECT * FROM questions WHERE calendar_id = $1 ORDER BY position ASC", calendar_id)
        return [dict(r) for r in rows]
