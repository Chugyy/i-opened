"""asyncpg connection pool — lifecycle managed via FastAPI lifespan."""

import asyncpg
from fastapi import FastAPI

from config.config import settings


async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password or "",
        min_size=2,
        max_size=10,
    )


def setup_pool(app: FastAPI) -> None:
    """Register pool open/close on the app lifespan (called from lifespan ctx)."""

    async def open_pool() -> None:
        app.state.pool = await create_pool()

    async def close_pool() -> None:
        await app.state.pool.close()

    app.state._open_pool = open_pool
    app.state._close_pool = close_pool
