import pytest
import uuid
import asyncpg
from config.config import settings
from app.database.crud.qualification_rule import create, update, delete, list_by_calendar
from app.database.crud.calendar import create as create_calendar
from app.database.crud.question import create as create_question
from app.database.crud.user import create as create_user


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
        await conn.execute("DELETE FROM qualification_rules")
        await conn.execute("DELETE FROM questions")
        await conn.execute("DELETE FROM calendars")
        await conn.execute("DELETE FROM users")
    await p.close()


@pytest.fixture
async def setup_data(pool):
    """Create user, calendar and question for FK constraints."""
    user = await create_user(pool, email=f"test-{uuid.uuid4()}@test.com", full_name="Test User", password_hash="hashed")
    cal = await create_calendar(pool, id=uuid.uuid4(), user_id=user["id"], name="Test Cal", slug=f"test-{uuid.uuid4()}", description="", slot_duration=30)
    question = await create_question(pool, calendar_id=cal["id"], label="Budget ?", type="number", options=None, position=1, required=True)
    return {"user": user, "calendar": cal, "question": question}


async def test_create_with_disqualify_values(pool, setup_data):
    result = await create(
        pool,
        calendar_id=setup_data["calendar"]["id"],
        question_id=setup_data["question"]["id"],
        disqualify_values=["< 5000"],
    )
    assert result["id"] is not None
    assert result["disqualify_values"] is not None
    assert result["min_length"] is None


async def test_create_with_min_value(pool, setup_data):
    result = await create(
        pool,
        calendar_id=setup_data["calendar"]["id"],
        question_id=setup_data["question"]["id"],
        min_value=5000.0,
    )
    assert result["id"] is not None
    assert float(result["min_value"]) == 5000.0


async def test_create_with_text_criteria(pool, setup_data):
    result = await create(
        pool,
        calendar_id=setup_data["calendar"]["id"],
        question_id=setup_data["question"]["id"],
        min_length=10,
        contains_keywords=["budget", "projet"],
    )
    assert result["id"] is not None
    assert result["min_length"] == 10
    assert result["contains_keywords"] is not None


async def test_update(pool, setup_data):
    created = await create(
        pool,
        calendar_id=setup_data["calendar"]["id"],
        question_id=setup_data["question"]["id"],
        min_value=1000.0,
    )
    updated = await update(pool, created["id"], {"min_value": 2000.0})
    assert updated is not None
    assert float(updated["min_value"]) == 2000.0


async def test_delete(pool, setup_data):
    created = await create(
        pool,
        calendar_id=setup_data["calendar"]["id"],
        question_id=setup_data["question"]["id"],
        disqualify_values=["test"],
    )
    deleted = await delete(pool, created["id"])
    assert deleted is True


async def test_delete_not_found(pool):
    result = await delete(pool, id=uuid.uuid4())
    assert result is False


async def test_list_by_calendar_empty(pool, setup_data):
    results = await list_by_calendar(pool, calendar_id=setup_data["calendar"]["id"])
    assert results == []


async def test_list_by_calendar_returns_all(pool, setup_data):
    await create(
        pool,
        calendar_id=setup_data["calendar"]["id"],
        question_id=setup_data["question"]["id"],
        disqualify_values=["test"],
    )
    results = await list_by_calendar(pool, calendar_id=setup_data["calendar"]["id"])
    assert len(results) >= 1
    assert "question_label" in results[0]
