"""WhatsApp service — sends messages via Unipile API.

Adapted from lib/tools/whatsapp UnipileWhatsAppClient.
"""

import logging
import re

import httpx

from config.config import settings

logger = logging.getLogger(__name__)


class WhatsAppError(Exception):
    pass


class PhoneNotOnWhatsAppError(WhatsAppError):
    pass


class InvalidPhoneNumberError(WhatsAppError):
    pass


def _validate_phone(phone: str) -> None:
    """Validate E.164 phone format."""
    if not re.match(r"^\+[1-9]\d{6,14}$", phone):
        raise InvalidPhoneNumberError(f"Invalid phone number format: {phone}")


async def check_whatsapp_exists(phone: str) -> bool:
    """Check if a phone number is registered on WhatsApp.

    Uses Unipile GET /users/{identifier} endpoint.
    Returns True if exists, False otherwise.
    """
    _validate_phone(phone)
    phone_identifier = phone.lstrip("+")

    async with httpx.AsyncClient(
        base_url=settings.unipile_dsn,
        headers={"X-API-KEY": settings.unipile_api_key},
        timeout=10.0,
    ) as client:
        try:
            resp = await client.get(
                f"/api/v1/users/{phone_identifier}",
                params={"account_id": settings.unipile_account_id},
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error("WhatsApp check_exists failed for %s: %s", phone, e)
            return False


async def send_whatsapp(phone: str, text: str) -> bool:
    """Send a WhatsApp message to a phone number.

    Starts a new conversation via Unipile API (form-data, not JSON).
    Returns True if sent, False on error.
    """
    _validate_phone(phone)

    async with httpx.AsyncClient(
        base_url=settings.unipile_dsn,
        headers={"X-API-KEY": settings.unipile_api_key},
        timeout=15.0,
    ) as client:
        try:
            resp = await client.post(
                "/api/v1/chats",
                data={
                    "account_id": settings.unipile_account_id,
                    "text": text,
                    "attendees_ids": phone,
                },
            )

            if resp.status_code in (200, 201):
                logger.info("WhatsApp sent to %s", phone)
                return True
            else:
                logger.error(
                    "WhatsApp send failed — status %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return False
        except Exception as e:
            logger.error("WhatsApp send error to %s: %s", phone, e)
            return False
