"""
Integration tests for Google Calendar service.
Uses real API keys — tests skip if credentials are not configured.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from config.config import settings
from app.core.services.google_calendar import (
    connect_google,
    refresh_token,
    fetch_events,
    push_event,
    delete_event,
    OAuthError,
    OAuthRevokedError,
    SyncTokenExpiredError,
    GoogleCalendarError,
)

HAS_GOOGLE_CREDS = bool(settings.google_client_id and settings.google_client_secret)


@pytest.mark.skipif(not HAS_GOOGLE_CREDS, reason="No Google API credentials configured")
class TestConnectGoogle:
    """OAuth2 code exchange tests."""

    def test_invalid_code_raises_oauth_error(self):
        """Invalid authorization code should raise OAuthError."""
        with pytest.raises(OAuthError):
            connect_google(
                code="invalid_code_xxx",
                redirect_uri=settings.google_redirect_uri or "http://localhost:8000/oauth/google/callback",
            )


@pytest.mark.skipif(not HAS_GOOGLE_CREDS, reason="No Google API credentials configured")
class TestRefreshToken:
    """Token refresh tests."""

    def test_invalid_refresh_token_raises_revoked(self):
        """Invalid refresh token should raise OAuthRevokedError."""
        with pytest.raises(OAuthRevokedError):
            refresh_token("invalid_refresh_token_xxx")


@pytest.mark.skipif(not HAS_GOOGLE_CREDS, reason="No Google API credentials configured")
class TestFetchEvents:
    """Event fetching tests. Requires a valid access_token."""

    def test_invalid_access_token_raises_error(self):
        """Invalid access token should raise GoogleCalendarError."""
        with pytest.raises(GoogleCalendarError):
            fetch_events(access_token="invalid_token_xxx")

    def test_invalid_sync_token_raises_expired(self):
        """
        Invalid sync token should raise SyncTokenExpiredError (410)
        or GoogleCalendarError (401 if token is also bad).
        """
        with pytest.raises((SyncTokenExpiredError, GoogleCalendarError)):
            fetch_events(access_token="invalid_token_xxx", sync_token="invalid_sync_token")


@pytest.mark.skipif(not HAS_GOOGLE_CREDS, reason="No Google API credentials configured")
class TestPushEvent:
    """Event creation tests. Requires a valid access_token."""

    def test_invalid_token_raises_error(self):
        """Push with invalid token should raise GoogleCalendarError."""
        booking = {
            "id": uuid4(),
            "start_time": datetime.now(timezone.utc) + timedelta(hours=1),
            "end_time": datetime.now(timezone.utc) + timedelta(hours=2),
            "prospect_name": "Test User",
            "prospect_email": "test@example.com",
        }
        with pytest.raises(GoogleCalendarError):
            push_event(access_token="invalid_token_xxx", booking=booking)


@pytest.mark.skipif(not HAS_GOOGLE_CREDS, reason="No Google API credentials configured")
class TestDeleteEvent:
    """Event deletion tests. Requires a valid access_token."""

    def test_invalid_token_raises_error(self):
        """Delete with invalid token should raise GoogleCalendarError."""
        with pytest.raises((GoogleCalendarError, OAuthRevokedError)):
            delete_event(access_token="invalid_token_xxx", google_event_id="nonexistent_id")
