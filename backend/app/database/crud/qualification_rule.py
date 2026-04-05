"""CRUD operations for qualification_rule."""

import json
from uuid import UUID

import asyncpg


async def create(pool: asyncpg.Pool, calendar_id: UUID, question_id: UUID, disqualify_values: list | None = None, min_length: int | None = None, contains_keywords: list | None = None, min_value: float | None = None) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO qualification_rules (calendar_id, question_id, disqualify_values, min_length, contains_keywords, min_value, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, now(), now()) RETURNING *",
            calendar_id,
            question_id,
            json.dumps(disqualify_values) if disqualify_values else None,
            min_length,
            json.dumps(contains_keywords) if contains_keywords else None,
            min_value,
        )
        return dict(row)


async def update(pool: asyncpg.Pool, rule_id: UUID, fields: dict) -> dict | None:
    if not fields:
        return None
    # Serialize JSONB fields
    for key in ("disqualify_values", "contains_keywords"):
        if key in fields and isinstance(fields[key], list):
            fields[key] = json.dumps(fields[key])
    assignments = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(fields))
    query = f"UPDATE qualification_rules SET {assignments}, updated_at = now() WHERE id = $1 RETURNING *"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, rule_id, *fields.values())
        return dict(row) if row else None


async def delete(pool: asyncpg.Pool, rule_id: UUID) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM qualification_rules WHERE id = $1 RETURNING id",
            rule_id,
        )
        return row is not None


async def list_by_calendar(pool: asyncpg.Pool, calendar_id: UUID) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT qr.*, q.label AS question_label, q.type AS question_type FROM qualification_rules qr JOIN questions q ON q.id = qr.question_id WHERE qr.calendar_id = $1 ORDER BY qr.created_at ASC",
            calendar_id,
        )
        return [dict(r) for r in rows]
