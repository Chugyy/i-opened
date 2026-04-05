import pytest
import asyncpg
from config.config import settings
from app.database.crud.user import create, get_by_email, update


@pytest.fixture
async def pool():
    p = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password or "",
        min_size=1,
        max_size=3,
    )
    yield p
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM users")
    await p.close()


async def test_create(pool):
    result = await create(pool, email="Email value", full_name="Full_Name value", password_hash="Password_Hash value")
    assert result["id"] is not None
    assert result["email"] == "Email value"
    assert result["full_name"] == "Full_Name value"
    assert result["password_hash"] == "Password_Hash value"


async def test_update_not_found(pool):
    result = await update(pool, 999999)
    assert result is None

