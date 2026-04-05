"""OAuth2 callback route."""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.api.deps import get_current_user, get_pool
from app.core.services.google_calendar import OAuthError, connect_google
from app.database.crud import calendar_sync as sync_crud
from config.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/oauth", tags=["oauth"])

_REDIRECT_URI = f"{settings.frontend_url}/api/oauth/google/callback"


@router.get("/google/callback")
async def google_oauth_callback(
    state: str,
    code: Optional[str] = None,
    scope: Optional[str] = None,
    error: Optional[str] = None,
    pool=Depends(get_pool),
):
    # Decode state — expected format: "{calendar_id}:{csrf_token}"
    try:
        calendar_id, _ = state.split(":", 1)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    base_redirect = f"{settings.frontend_url}/calendars/{calendar_id}/settings"

    # User denied consent
    if error == "access_denied" or not code:
        return RedirectResponse(url=f"{base_redirect}?sync=error&reason=access_denied")

    # Exchange code for tokens
    try:
        tokens = connect_google(code=code, redirect_uri=_REDIRECT_URI)
    except OAuthError as e:
        logger.error("OAuth code exchange failed for calendar %s: %s", calendar_id, e)
        return RedirectResponse(url=f"{base_redirect}?sync=error&reason=invalid_code")

    # Required scope check
    if scope and "calendar" not in scope:
        return RedirectResponse(url=f"{base_redirect}?sync=error&reason=missing_scope")

    # Persist tokens
    try:
        existing = await sync_crud.get_by_calendar(pool, calendar_id=calendar_id)
        if existing:
            await sync_crud.update(
                pool,
                calendar_id=calendar_id,
                fields={
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_expiry": tokens["token_expiry"],
                    "status": "connected",
                },
            )
        else:
            await sync_crud.create(
                pool,
                id=uuid4(),
                calendar_id=calendar_id,
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                token_expiry=tokens["token_expiry"],
                sync_token=None,
            )
    except Exception as e:
        logger.error("Failed to persist calendar sync for %s: %s", calendar_id, e)
        return RedirectResponse(url=f"{base_redirect}?sync=error&reason=internal_error")

    return RedirectResponse(url=f"{base_redirect}?sync=connected")
