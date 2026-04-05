from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt, JWTError, ExpiredSignatureError
from config.config import settings


class TokenExpiredError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def generate_tokens(user_id: int, email: str) -> dict:
    now = datetime.now(timezone.utc)

    access_payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": now + timedelta(hours=settings.jwt_expiration_hours),
        "iat": now,
    }
    refresh_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": now + timedelta(days=7),
        "iat": now,
    }

    access_token = jwt.encode(access_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    refresh_token = jwt.encode(refresh_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    return {"access_token": access_token, "refresh_token": refresh_token}


def verify_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except JWTError:
        raise InvalidTokenError("Invalid token")

    if payload.get("type") != expected_type:
        raise InvalidTokenError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")

    return payload
