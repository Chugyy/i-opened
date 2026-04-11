"""Email service — sends transactional emails via SMTP.

Adapted from lib/tools/email imap_smtp_client.
"""

import logging
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to: str,
    subject: str,
    body: str,
    html: bool = True,
    ics_data: bytes | None = None,
) -> bool:
    """Send an email via SMTP.

    Uses SMTP credentials from settings (env vars).
    If ics_data is provided, attaches a .ics calendar invitation that triggers
    Accept/Decline buttons in Gmail, Outlook, and Apple Mail.
    Returns True if sent, False on error.
    """
    try:
        if ics_data is not None:
            # Mixed message: HTML body + calendar invitation
            msg = MIMEMultipart("mixed")

            # Alternative part: HTML + text/calendar (triggers inline Accept/Decline)
            alt = MIMEMultipart("alternative")
            if html:
                alt.attach(MIMEText(body, "html"))
            else:
                alt.attach(MIMEText(body, "plain"))

            # Inline calendar part — this is what makes Gmail/Outlook show the buttons
            cal_part = MIMEText(ics_data.decode("utf-8"), "calendar", "utf-8")
            cal_part.replace_header("Content-Type", "text/calendar; method=REQUEST; charset=UTF-8")
            alt.attach(cal_part)

            msg.attach(alt)

            # Also attach as .ics file for clients that don't support inline calendar
            attachment = MIMEBase("application", "ics")
            attachment.set_payload(ics_data)
            attachment.add_header("Content-Disposition", "attachment", filename="invitation.ics")
            attachment.add_header("Content-Type", "text/calendar; method=REQUEST; charset=UTF-8; name=invitation.ics")
            msg.attach(attachment)
        elif html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "html"))
        else:
            msg = MIMEText(body, "plain")

        msg["From"] = settings.smtp_email
        msg["To"] = to
        msg["Subject"] = subject

        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.smtp_email, settings.smtp_password)
        server.send_message(msg)
        server.quit()

        logger.info("Email sent to %s — subject: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_booking_confirmation(
    to: str,
    prospect_name: str,
    calendar_name: str,
    date_str: str,
    ics_data: bytes | None = None,
) -> bool:
    """Send booking confirmation email to prospect with optional .ics invitation."""
    subject = f"Confirmation de votre RDV — {calendar_name}"
    body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Votre RDV est confirmé !</h2>
        <p>Bonjour {prospect_name},</p>
        <p>Votre rendez-vous <strong>{calendar_name}</strong> est confirmé pour le :</p>
        <p style="font-size: 18px; font-weight: bold; color: #4F46E5;">{date_str}</p>
        <p>L'invitation a été jointe à cet email. Cliquez sur <strong>Accepter</strong> pour l'ajouter à votre agenda.</p>
        <p>À bientôt !</p>
    </div>
    """
    return send_email(to=to, subject=subject, body=body, html=True, ics_data=ics_data)


def send_booking_notification_to_admin(
    admin_email: str,
    prospect_name: str,
    prospect_email: str,
    calendar_name: str,
    date_str: str,
    lead_id: str,
) -> bool:
    """Send notification to admin when a booking is created."""
    subject = f"Nouveau RDV — {prospect_name}"
    body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Nouveau rendez-vous</h2>
        <p><strong>{prospect_name}</strong> ({prospect_email}) a pris un RDV :</p>
        <ul>
            <li>Calendrier : {calendar_name}</li>
            <li>Date : {date_str}</li>
        </ul>
        <p><a href="{settings.app_url}/leads/{lead_id}">Voir le lead</a></p>
    </div>
    """
    return send_email(to=admin_email, subject=subject, body=body, html=True)


def send_cancellation_email(
    to: str,
    prospect_name: str,
    calendar_name: str,
    reason: str,
) -> bool:
    """Send booking cancellation email to prospect."""
    subject = f"Annulation de votre RDV — {calendar_name}"
    body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>RDV annulé</h2>
        <p>Bonjour {prospect_name},</p>
        <p>Votre rendez-vous <strong>{calendar_name}</strong> a été annulé.</p>
        <p>Raison : {reason}</p>
        <p>N'hésitez pas à reprendre un créneau.</p>
    </div>
    """
    return send_email(to=to, subject=subject, body=body, html=True)
