"""Auth routes — setup, login, refresh, profile."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_pool
from app.api.models.user import (
    LoginRequest,
    RefreshRequest,
    SetupAdminRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)
from app.core.jobs.user import ConflictError, setup_admin
from app.core.utils.user import (
    InvalidTokenError,
    TokenExpiredError,
    generate_tokens,
    verify_password,
    verify_token,
)
from app.database.crud.user import get_by_email, update

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/setup", response_model=TokenResponse, status_code=201)
async def setup_admin_endpoint(data: SetupAdminRequest, pool=Depends(get_pool)):
    try:
        tokens = await setup_admin(
            pool,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
        )
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(data: LoginRequest, pool=Depends(get_pool)):
    user = await get_by_email(pool, data.email)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    tokens = generate_tokens(user_id=user["id"], email=user["email"])
    return {**tokens, "token_type": "bearer"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_endpoint(data: RefreshRequest):
    try:
        payload = verify_token(data.refresh_token, expected_type="refresh")
    except TokenExpiredError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="TOKEN_EXPIRED")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_TOKEN")

    tokens = generate_tokens(user_id=payload["sub"], email=payload.get("email", ""))
    return {**tokens, "token_type": "bearer"}


@router.get("/me", response_model=UserProfileResponse)
async def get_me_endpoint(current_user=Depends(get_current_user), pool=Depends(get_pool)):
    user = await get_by_email(pool, current_user.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/me", response_model=UserProfileResponse)
async def update_me_endpoint(
    data: UpdateProfileRequest,
    current_user=Depends(get_current_user),
    pool=Depends(get_pool),
):
    fields = data.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided")

    user = await get_by_email(pool, current_user.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated = await update(pool, user_id=str(user["id"]), fields=fields)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated
