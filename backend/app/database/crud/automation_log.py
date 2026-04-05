"""CRUD operations for automation_log."""

from datetime import datetime
from uuid import UUID

import asyncpg


async def create(pool: asyncpg.Pool, automation_id: UUID, automation_step_id: UUID, lead_id: UUID, trigger: str, scheduled_at: datetime) -> dict:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO automation_logs (automation_id, automation_step_id, lead_id, trigger, status, scheduled_at, created_at, updated_at) VALUES ($1, $2, $3, $4, 'pending', $5, now(), now()) RETURNING *",
            automation_id,
            automation_step_id,
            lead_id,
            trigger,
            scheduled_at,
        )
        return dict(row)


async def update_status(pool: asyncpg.Pool, log_id: UUID, status: str, error_message: str | None = None, sent_at: datetime | None = None) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE automation_logs SET status = $2, error_message = COALESCE($3, error_message), sent_at = COALESCE($4, sent_at), updated_at = now() WHERE id = $1 RETURNING *",
            log_id,
            status,
            error_message,
            sent_at,
        )
        return dict(row) if row else None


async def list_pending(pool: asyncpg.Pool, up_to: datetime) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM automation_logs WHERE status = 'pending' AND scheduled_at <= $1 ORDER BY scheduled_at ASC", up_to)
        return [dict(r) for r in rows]


async def list_by_lead(pool: asyncpg.Pool, lead_id: UUID) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM automation_logs WHERE lead_id = $1 ORDER BY created_at DESC", lead_id)
        return [dict(r) for r in rows]


async def list_by_automation(pool: asyncpg.Pool, automation_id: UUID) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM automation_logs WHERE automation_id = $1 ORDER BY created_at DESC", automation_id)
        return [dict(r) for r in rows]


async def cancel_by_lead_and_trigger(pool: asyncpg.Pool, lead_id: UUID, triggers: list[str]) -> int:
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE automation_logs SET status = 'cancelled', updated_at = now() WHERE lead_id = $1 AND trigger = ANY($2) AND status = 'pending'",
            lead_id,
            triggers,
        )
        return int(result.split()[-1])


async def cancel_pending_logs(pool: asyncpg.Pool, automation_id: UUID) -> int:
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE automation_logs SET status = 'cancelled', updated_at = now() WHERE automation_id = $1 AND status = 'pending'",
            automation_id,
        )
        return int(result.split()[-1])
