"""Automation execution jobs — process pending automation logs.

Worker: process_automation_queue (called every minute by scheduler)
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

import asyncpg

from config.config import settings
from app.core.services.email_service import send_email
from app.core.services.whatsapp_service import check_whatsapp_exists, send_whatsapp
from app.core.utils.automation_step import resolve_variables
from app.database.crud import automation as automation_crud
from app.database.crud import automation_log as log_crud
from app.database.crud import automation_step as step_crud
from app.database.crud import lead as lead_crud

logger = logging.getLogger(__name__)


async def execute_step(
    pool: asyncpg.Pool,
    log: dict,
) -> str:
    """Execute a single automation step (send email or WhatsApp).

    Returns "sent" or "failed".
    """
    log_id = log["id"]

    # Get the step details
    step = await step_crud.get(pool, step_id=log["automation_step_id"])
    if not step:
        await log_crud.update_status(pool, log_id=log_id, status="failed", error_message="step_not_found")
        return "failed"

    # Get lead details for variable interpolation
    lead = await lead_crud.get_detail(pool, lead_id=log["lead_id"])
    if not lead:
        await log_crud.update_status(pool, log_id=log_id, status="failed", error_message="lead_not_found")
        return "failed"

    # Fetch calendar name for {calendrier} variable
    calendar_name = ""
    try:
        from app.database.crud import calendar as calendar_crud
        cal = await calendar_crud.get(pool, calendar_id=lead.get("calendar_id"))
        if cal:
            calendar_name = cal.get("name", "")
    except Exception:
        pass

    # Fetch booking date for {date_rdv} variable
    date_rdv = "N/A"
    try:
        from app.database.crud import booking as booking_crud
        bookings = await booking_crud.list_by_lead(pool, lead_id=log["lead_id"])
        if bookings:
            from datetime import timezone as _tz
            dt = bookings[0].get("starts_at")
            if dt:
                if hasattr(dt, "strftime"):
                    date_rdv = dt.strftime("%A %d %B %Y à %H:%M")
                else:
                    date_rdv = str(dt)
    except Exception:
        pass

    # Resolve variables in content
    context = {
        "prenom": lead.get("first_name", ""),
        "nom": lead.get("last_name", ""),
        "email": lead.get("email", ""),
        "telephone": lead.get("phone", ""),
        "date_rdv": date_rdv,
        "calendrier": calendar_name,
    }
    body = resolve_variables(step["content"], context, trigger=log.get("trigger", ""))
    channel = step["channel"]

    if channel == "email":
        subject = f"Rappel — votre rendez-vous"

        # Generate .ics invitation for booking confirmation emails
        ics_data = None
        if log.get("trigger") == "booking_confirme":
            try:
                from app.core.utils.ical import generate_ics
                from app.database.crud import booking as booking_crud
                from app.database.crud import calendar as cal_crud
                from app.database.crud import user as user_crud

                bookings = await booking_crud.list_by_lead(pool, lead_id=log["lead_id"])
                if bookings:
                    bk = bookings[0]
                    cal = await cal_crud.get(pool, calendar_id=lead.get("calendar_id"))
                    admin = await user_crud.get_by_id(pool, user_id=cal["user_id"]) if cal else None

                    prospect_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
                    organizer_email = admin["email"] if admin else settings.smtp_email
                    organizer_name = admin.get("full_name", "I-Opened") if admin else "I-Opened"

                    ics_data = generate_ics(
                        booking_id=bk["id"],
                        starts_at=bk["starts_at"],
                        ends_at=bk["ends_at"],
                        summary=f"RDV — {calendar_name}" if calendar_name else "Votre rendez-vous",
                        organizer_email=organizer_email,
                        organizer_name=organizer_name,
                        attendee_email=lead["email"],
                        attendee_name=prospect_name,
                        description=f"Rendez-vous {calendar_name} confirmé via I-Opened",
                    )
                    subject = f"Confirmation de votre RDV — {calendar_name}"
            except Exception as e:
                logger.warning("Failed to generate .ics for log %s: %s", log_id, e)

        success = send_email(to=lead["email"], subject=subject, body=body, html=True, ics_data=ics_data)
        if success:
            await log_crud.update_status(
                pool, log_id=log_id, status="sent",
                sent_at=datetime.now(timezone.utc),
            )
            return "sent"
        else:
            await log_crud.update_status(
                pool, log_id=log_id, status="failed",
                error_message="email_send_failed",
            )
            return "failed"

    elif channel == "whatsapp":
        phone = lead.get("phone", "")
        if not phone:
            await log_crud.update_status(pool, log_id=log_id, status="failed", error_message="no_phone")
            return "failed"

        exists = await check_whatsapp_exists(phone)
        if not exists:
            await log_crud.update_status(pool, log_id=log_id, status="failed", error_message="phone_not_on_whatsapp")
            return "failed"

        success = await send_whatsapp(phone, body)
        if success:
            await log_crud.update_status(
                pool, log_id=log_id, status="sent",
                sent_at=datetime.now(timezone.utc),
            )
            return "sent"
        else:
            await log_crud.update_status(pool, log_id=log_id, status="failed", error_message="whatsapp_send_failed")
            return "failed"

    else:
        await log_crud.update_status(pool, log_id=log_id, status="failed", error_message=f"unknown_channel_{channel}")
        return "failed"


async def process_automation_queue(pool: asyncpg.Pool) -> dict:
    """Process all pending automation logs whose scheduled_at <= now.

    Called by the scheduler every minute.
    Returns {processed, sent, failed}.
    """
    now = datetime.now(timezone.utc)
    pending = await log_crud.list_pending(pool, up_to=now)

    if not pending:
        return {"processed": 0, "sent": 0, "failed": 0}

    sent_count = 0
    failed_count = 0

    for log in pending:
        # Check automation is still active
        automation = await automation_crud.get(pool, automation_id=log["automation_id"])
        if not automation or not automation.get("is_active", False):
            await log_crud.update_status(pool, log_id=log["id"], status="cancelled")
            continue

        result = await execute_step(pool, log)
        if result == "sent":
            sent_count += 1
        else:
            failed_count += 1

    return {
        "processed": len(pending),
        "sent": sent_count,
        "failed": failed_count,
    }


async def schedule_automation(
    pool: asyncpg.Pool,
    lead_id,
    trigger: str,
    calendar_id,
    booking: dict | None = None,
) -> int:
    """Create pending logs for all automations matching this trigger/calendar.

    Returns number of logs created.
    """
    from datetime import timedelta

    automations = await automation_crud.list(
        pool, user_id=None, calendar_id=calendar_id, trigger=trigger,
    )

    count = 0
    for auto in automations:
        if not auto.get("is_active", False):
            continue

        steps = await step_crud.list_by_automation(pool, automation_id=auto["id"])

        for step in steps:
            delay_value = step.get("delay_value", 1)
            delay_unit = step.get("delay_unit", "hours")
            if delay_unit == "minutes":
                delta = timedelta(minutes=delay_value)
            elif delay_unit == "hours":
                delta = timedelta(hours=delay_value)
            else:
                delta = timedelta(days=delay_value)

            if trigger == "avant_rdv" and booking:
                scheduled_at = booking["starts_at"] - delta
            elif trigger == "apres_rdv" and booking:
                scheduled_at = booking["ends_at"] + delta
            elif trigger == "booking_confirme":
                # Immediately after booking + delay
                scheduled_at = datetime.now(timezone.utc) + delta
            else:
                # sans_booking triggers use lead.created_at + delay
                lead = await lead_crud.get_detail(pool, lead_id=lead_id)
                created_at = lead["created_at"] if lead else datetime.now(timezone.utc)
                scheduled_at = created_at + delta

            # Skip only if scheduled far in the past (> 24h ago) — allows delay=0 (instant)
            if scheduled_at < datetime.now(timezone.utc) - timedelta(hours=24):
                continue

            await log_crud.create(
                pool,
                automation_id=auto["id"],
                automation_step_id=step["id"],
                lead_id=lead_id,
                trigger=trigger,
                scheduled_at=scheduled_at,
            )
            count += 1

    return count


async def cancel_pending_for_lead(
    pool: asyncpg.Pool,
    lead_id,
    triggers: list[str],
) -> int:
    """Cancel pending automations for a lead (e.g. when they book)."""
    return await log_crud.cancel_by_lead_and_trigger(pool, lead_id=lead_id, triggers=triggers)
