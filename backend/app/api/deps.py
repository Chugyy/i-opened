"""FastAPI dependency injectors."""

from types import SimpleNamespace
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from config.config import settings

_bearer = HTTPBearer()


def get_pool(request: Request):
    return request.app.state.pool


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    pool=Depends(get_pool),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOKEN_EXPIRED")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_TOKEN")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_TOKEN")

    return SimpleNamespace(
        id=UUID(payload["sub"]),
        email=payload.get("email", ""),
    )
