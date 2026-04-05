"""
Google Calendar integration.
Doc: https://developers.google.com/calendar/api/v3/reference

OAuth2 flow + Calendar events CRUD + incremental sync.
"""

import logging
from typing import Optional

from google.auth.exceptions import RefreshError, TransportError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.config import settings

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
REQUEST_TIMEOUT = 10  # seconds


# === Exceptions ===

class GoogleCalendarError(Exception):
    """Base error for Google Calendar operations."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class OAuthError(GoogleCalendarError):
    """OAuth2 exchange or configuration error."""
    pass


class OAuthRevokedError(GoogleCalendarError):
    """Token revoked or permanently invalid."""
    pass


class SyncTokenExpiredError(GoogleCalendarError):
    """Sync token expired (HTTP 410). Caller must do a full resync."""
    pass


# === Internal helpers ===

def _build_service(access_token: str):
    """Build a Google Calendar API service from an access token."""
    creds = Credentials(token=access_token)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


# === Functions ===

def connect_google(code: str, redirect_uri: str) -> dict:
    """
    Exchange OAuth2 authorization code for tokens.
    Called by: calendar_sync routes (POST /oauth/google/callback)

    Returns: {access_token, refresh_token, token_expiry}
    """
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        return {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_expiry": creds.expiry,
        }
    except Exception as e:
        logger.error("OAuth2 code exchange failed: %s", e)
        raise OAuthError(f"OAuth2 code exchange failed: {e}")


def refresh_token(refresh_tok: str) -> dict:
    """
    Refresh an expired access token.
    Called by: sync_calendar job (step 3)

    Returns: {access_token, token_expiry}
    Raises OAuthRevokedError if token is revoked.
    """
    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_tok,
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        creds.refresh(Request())

        return {
            "access_token": creds.token,
            "token_expiry": creds.expiry,
        }
    except Exception as e:
        error_str = str(e).lower()
        if "revoked" in error_str or "invalid_grant" in error_str:
            raise OAuthRevokedError(f"Token revoked: {e}")
        logger.error("Token refresh failed: %s", e)
        raise OAuthRevokedError(f"Token refresh failed: {e}")


def fetch_events(access_token: str, sync_token: Optional[str] = None) -> dict:
    """
    Fetch calendar events with incremental sync support.
    Called by: sync_calendar job (step 4)

    If sync_token provided: incremental sync.
    If sync_token is None: full sync (timeMin=now).
    Filters out events tagged source="i-opened" to avoid sync loops.

    Returns: {events: list[dict], next_sync_token: str}
    Raises SyncTokenExpiredError on HTTP 410.
    """
    from datetime import datetime, timezone

    service = _build_service(access_token)
    all_events = []
    page_token = None

    try:
        while True:
            kwargs = {
                "calendarId": "primary",
                "singleEvents": True,
                "maxResults": 250,
            }

            if sync_token and page_token is None:
                kwargs["syncToken"] = sync_token
            elif not sync_token and page_token is None:
                kwargs["timeMin"] = datetime.now(timezone.utc).isoformat()

            if page_token:
                kwargs["pageToken"] = page_token

            result = service.events().list(**kwargs).execute()

            for event in result.get("items", []):
                # Filter out events created by I-Opened (anti-loop)
                ext_props = event.get("extendedProperties", {})
                private_props = ext_props.get("private", {})
                if private_props.get("source") == "i-opened":
                    continue
                all_events.append(event)

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        return {
            "events": all_events,
            "next_sync_token": result.get("nextSyncToken", ""),
        }

    except HttpError as e:
        if e.resp.status == 410:
            raise SyncTokenExpiredError("Sync token expired (410 Gone)")
        if e.resp.status in (401, 403):
            raise OAuthRevokedError(f"Auth failed: {e}")
        logger.error("fetch_events failed: %s", e)
        raise GoogleCalendarError(f"Fetch events failed: {e}", status_code=e.resp.status)
    except RefreshError as e:
        raise GoogleCalendarError(f"Invalid credentials: {e}", status_code=401)
    except TransportError as e:
        raise GoogleCalendarError(f"Transport error: {e}")


def push_event(access_token: str, booking: dict) -> dict:
    """
    Create a Google Calendar event for a booking.
    Called by: booking creation job

    Tags event with extendedProperties.private.source="i-opened" + booking_id.

    Returns: {google_event_id: str}
    """
    service = _build_service(access_token)

    event_body = {
        "summary": f"Booking: {booking.get('prospect_name', 'Unknown')}",
        "start": {
            "dateTime": booking["start_time"].isoformat()
            if hasattr(booking["start_time"], "isoformat")
            else booking["start_time"],
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": booking["end_time"].isoformat()
            if hasattr(booking["end_time"], "isoformat")
            else booking["end_time"],
            "timeZone": "UTC",
        },
        "attendees": [
            {"email": booking["prospect_email"]}
        ] if booking.get("prospect_email") else [],
        "extendedProperties": {
            "private": {
                "source": "i-opened",
                "booking_id": str(booking["id"]),
            }
        },
    }

    try:
        result = service.events().insert(calendarId="primary", body=event_body).execute()
        return {"google_event_id": result["id"]}
    except HttpError as e:
        logger.error("push_event failed: %s", e)
        raise GoogleCalendarError(f"Push event failed: {e}", status_code=e.resp.status)
    except RefreshError as e:
        raise GoogleCalendarError(f"Invalid credentials: {e}", status_code=401)
    except TransportError as e:
        raise GoogleCalendarError(f"Transport error: {e}")


def delete_event(access_token: str, google_event_id: str) -> bool:
    """
    Delete a Google Calendar event.
    Called by: booking cancellation job

    Returns True if deleted, False if already gone (404).
    Raises OAuthRevokedError on 403 (revoked access).
    """
    service = _build_service(access_token)

    try:
        service.events().delete(calendarId="primary", eventId=google_event_id).execute()
        return True
    except HttpError as e:
        if e.resp.status == 404:
            return False
        if e.resp.status == 403:
            raise OAuthRevokedError(f"Access revoked: {e}")
        logger.error("delete_event failed: %s", e)
        raise GoogleCalendarError(f"Delete event failed: {e}", status_code=e.resp.status)
    except RefreshError as e:
        raise GoogleCalendarError(f"Invalid credentials: {e}", status_code=401)
    except TransportError as e:
        raise GoogleCalendarError(f"Transport error: {e}")
