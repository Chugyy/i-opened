"""Telegram notification service for i-opened."""

import logging
from datetime import datetime

import httpx

from config.config import settings

logger = logging.getLogger(__name__)


async def notify(text: str, silent: bool = False) -> bool:
    """Send a Telegram message. Returns True on success."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.debug("Telegram not configured, skipping")
        return False
    try:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "chat_id": settings.telegram_chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_notification": silent,
            })
            return resp.status_code == 200
    except Exception as e:
        logger.warning("Telegram send failed: %s", e)
        return False


async def notify_new_lead(
    first_name: str,
    last_name: str,
    email: str,
    phone: str = "",
    source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    calendar_name: str = "",
    is_qualified: bool = True,
) -> bool:
    """Notify admin of a new lead via Telegram."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    source_line = ""
    if source or utm_medium or utm_campaign:
        parts = []
        if source:
            parts.append(source)
        if utm_medium:
            parts.append(utm_medium)
        if utm_campaign:
            parts.append(utm_campaign)
        source_line = f"\n🔗 Source : <b>{' / '.join(parts)}</b>"

    status = "✅ Qualifié" if is_qualified else "❌ Non qualifié"

    text = (
        f"🔔 <b>Nouveau lead I-Opened</b>\n\n"
        f"👤 {first_name} {last_name}\n"
        f"📧 {email}\n"
        f"📱 {phone or '—'}\n"
        f"📅 {calendar_name or '—'}\n"
        f"🏷️ {status}"
        f"{source_line}\n"
        f"🕐 {now}"
    )
    return await notify(text)
