"""Jobs for user entity."""

import asyncpg

from app.database.crud.user import count, create, get_by_email
from app.core.utils.user import generate_tokens, hash_password


class ConflictError(Exception):
    pass


async def setup_admin(pool: asyncpg.Pool, email: str, password: str, full_name: str) -> dict:
    # Mono-admin : le premier demarrage cree l'admin, ensuite /auth/setup est ferme.
    if await count(pool) > 0:
        raise ConflictError("Admin already exists")

    password_hash = hash_password(password)
    user = await create(pool, email=email, full_name=full_name, password_hash=password_hash)
    tokens = generate_tokens(user_id=user["id"], email=user["email"])
    return {**tokens, "token_type": "bearer"}
