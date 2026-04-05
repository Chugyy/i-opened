"""FastAPI application entrypoint."""

import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.calendar import router as calendar_router
from app.api.routes.booking import router as booking_router
from app.api.routes.book import router as book_router
from app.api.routes.automation import router as automation_router
from app.api.routes.lead import router as lead_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.oauth import router as oauth_router
from app.database.pool import create_pool
from config.config import settings

logger = logging.getLogger(__name__)


async def _run_migrations(pool):
    """Run SQL migrations in order."""
    migrations_dir = pathlib.Path(__file__).parent.parent / "database" / "migrations"
    if not migrations_dir.exists():
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    name VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            applied = {r["name"] for r in await conn.fetch("SELECT name FROM _migrations")}
            for sql_file in sorted(migrations_dir.glob("*.sql")):
                if sql_file.name not in applied:
                    logger.info("Applying migration: %s", sql_file.name)
                    await conn.execute(sql_file.read_text())
                    await conn.execute("INSERT INTO _migrations (name) VALUES ($1)", sql_file.name)
    except Exception as e:
        logger.warning("Migration skipped (likely concurrent worker): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.scheduler import start_scheduler, stop_scheduler
    app.state.pool = await create_pool()
    await _run_migrations(app.state.pool)
    start_scheduler(app.state.pool)
    yield
    stop_scheduler()
    await app.state.pool.close()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    redirect_slashes=False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(booking_router)
app.include_router(book_router)
app.include_router(automation_router)
app.include_router(lead_router)
app.include_router(dashboard_router)
app.include_router(oauth_router)
