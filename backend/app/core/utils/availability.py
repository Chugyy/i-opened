from datetime import time, datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo


def validate_availability(availabilities: list[dict]) -> tuple[list[str], list[str]]:
    """
    Validate availability entries.
    Returns (errors, warnings). Errors are blocking; warnings are not.
    """
    errors: list[str] = []
    warnings: list[str] = []
    has_active = False

    for entry in availabilities:
        if not entry.get("is_active"):
            continue

        has_active = True
        start: time = entry["start_time"]
        end: time = entry["end_time"]
        lunch_start: time | None = entry.get("lunch_start")
        lunch_end: time | None = entry.get("lunch_end")

        if end <= start:
            errors.append("end_time must be after start_time")

        lunch_partial = (lunch_start is None) != (lunch_end is None)
        if lunch_partial:
            errors.append("lunch_start and lunch_end must both be provided")
        elif lunch_start is not None and lunch_end is not None:
            if lunch_start < start or lunch_end > end:
                errors.append("lunch break must be within the work window")
            if lunch_end <= lunch_start:
                errors.append("lunch_end must be after lunch_start")

    if not has_active:
        warnings.append("No active day — no slots will be generated")

    return errors, warnings


def generate_slots(
    availability: dict,
    slot_duration: int,
    target_date: date,
    admin_tz: str = "Europe/Paris",
) -> list[datetime]:
    """
    Generate time slots for a given day based on an availability entry.
    Slots are generated in the admin's timezone, then converted to UTC.
    Returns list of slot start datetimes (timezone-aware, UTC).
    """
    if not availability.get("is_active"):
        return []

    start: time = availability["start_time"]
    end: time = availability["end_time"]
    lunch_start: time | None = availability.get("lunch_start")
    lunch_end: time | None = availability.get("lunch_end")

    total_minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
    if slot_duration > total_minutes:
        return []

    tz = ZoneInfo(admin_tz)
    utc = ZoneInfo("UTC")

    slots: list[datetime] = []
    current = datetime.combine(target_date, start, tzinfo=tz)
    end_dt = datetime.combine(target_date, end, tzinfo=tz)
    delta = timedelta(minutes=slot_duration)

    while current + delta <= end_dt:
        slot_end = current + delta

        if lunch_start is not None and lunch_end is not None:
            ls = datetime.combine(target_date, lunch_start, tzinfo=tz)
            le = datetime.combine(target_date, lunch_end, tzinfo=tz)
            if current < le and slot_end > ls:
                current += delta
                continue

        slots.append(current.astimezone(utc))
        current += delta

    return slots
