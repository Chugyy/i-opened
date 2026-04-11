"""Generate iCalendar (.ics) files for booking invitations (RFC 5545).

The generated .ics uses METHOD:REQUEST so that email clients (Gmail, Outlook,
Apple Mail) display Accept/Decline/Tentative buttons natively.
"""

from datetime import datetime
from uuid import UUID

from icalendar import Calendar, Event, vCalAddress, vText


def generate_ics(
    booking_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    summary: str,
    organizer_email: str,
    organizer_name: str,
    attendee_email: str,
    attendee_name: str,
    description: str = "",
    location: str = "",
) -> bytes:
    """Generate a .ics invitation as bytes.

    Uses booking_id as UID to ensure idempotence (same booking = same UID,
    no duplicate events in the attendee's calendar).
    """
    cal = Calendar()
    cal.add("prodid", "-//I-Opened//Booking//FR")
    cal.add("version", "2.0")
    cal.add("method", "REQUEST")
    cal.add("calscale", "GREGORIAN")

    event = Event()
    event.add("uid", f"{booking_id}@i-opened.multimodal-house.fr")
    event.add("dtstart", starts_at)
    event.add("dtend", ends_at)
    event.add("summary", summary)
    event.add("description", description)
    event.add("status", "CONFIRMED")
    event.add("sequence", 0)

    if location:
        event.add("location", location)

    # Organizer
    org = vCalAddress(f"mailto:{organizer_email}")
    org.params["cn"] = vText(organizer_name)
    org.params["role"] = vText("CHAIR")
    event.add("organizer", org)

    # Attendee (the prospect)
    att = vCalAddress(f"mailto:{attendee_email}")
    att.params["cn"] = vText(attendee_name)
    att.params["rsvp"] = vText("TRUE")
    att.params["partstat"] = vText("NEEDS-ACTION")
    att.params["role"] = vText("REQ-PARTICIPANT")
    event.add("attendee", att)

    cal.add_component(event)
    return cal.to_ical()
