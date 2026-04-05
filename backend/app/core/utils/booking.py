from datetime import datetime, timedelta


def _parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def compute_available_slots(
    all_slots: list[datetime],
    bookings: list[dict],
    gcal_events: list[dict],
    slot_duration: int,
) -> list[datetime]:
    """
    Filter theoretical slots by removing those blocked by existing bookings or
    Google Calendar events.

    Booking conflict: slot starts_at matches a booking's starts_at.
    GCal conflict: slot overlaps with event (slot_start < event_end AND slot_end > event_start).
    """
    delta = timedelta(minutes=slot_duration)

    # Build set of booked start times for O(1) lookup
    booked_starts = {_parse_dt(b["starts_at"]) for b in bookings}

    available: list[datetime] = []
    for slot in all_slots:
        if slot in booked_starts:
            continue

        slot_end = slot + delta

        blocked = False
        for event in gcal_events:
            event_start = _parse_dt(event["start"])
            event_end = _parse_dt(event["end"])
            if slot < event_end and slot_end > event_start:
                blocked = True
                break

        if not blocked:
            available.append(slot)

    return sorted(available)
