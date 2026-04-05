"""CRUD operations for user."""

from uuid import UUID

import asyncpg


async def create(pool: asyncpg.Pool, email: str, full_name: str, password_hash: str) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (email, full_name, password_hash, notifications_enabled, created_at, updated_at) VALUES ($1, $2, $3, true, now(), now()) RETURNING *",
            email,
            full_name,
            password_hash,
        )
        return dict(row)


async def get_by_id(pool: asyncpg.Pool, user_id: UUID | str) -> dict | None:
    uid = UUID(str(user_id))
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", uid)
        return dict(row) if row else None


async def get_by_email(pool: asyncpg.Pool, email: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE email = $1 LIMIT 1", email)
        return dict(row) if row else None


async def update(pool: asyncpg.Pool, user_id: UUID, fields: dict) -> dict | None:
    allowed = {"full_name", "notifications_enabled", "timezone"}
    filtered = {k: v for k, v in fields.items() if k in allowed}
    if not filtered:
        return None
    assignments = ", ".join(f"{col} = ${i + 2}" for i, col in enumerate(filtered))
    query = f"UPDATE users SET {assignments}, updated_at = now() WHERE id = $1 RETURNING *"
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, user_id, *filtered.values())
        return dict(row) if row else None
