import pytest
from datetime import time, date, datetime
from app.core.utils.availability import validate_availability, generate_slots


# --- validate_availability ---

def _entry(start="09:00", end="17:00", lunch_start=None, lunch_end=None, is_active=True, day=0):
    def t(s):
        h, m = map(int, s.split(":"))
        return time(h, m)

    return {
        "day_of_week": day,
        "start_time": t(start),
        "end_time": t(end),
        "lunch_start": t(lunch_start) if lunch_start else None,
        "lunch_end": t(lunch_end) if lunch_end else None,
        "is_active": is_active,
    }


def test_valid_no_lunch():
    errors, warnings = validate_availability([_entry()])
    assert errors == []
    assert warnings == []


def test_valid_with_lunch():
    errors, warnings = validate_availability([_entry(lunch_start="12:00", lunch_end="13:00")])
    assert errors == []
    assert warnings == []


def test_end_before_start():
    errors, _ = validate_availability([_entry(start="17:00", end="09:00")])
    assert any("end_time must be after start_time" in e for e in errors)


def test_end_equal_start():
    errors, _ = validate_availability([_entry(start="09:00", end="09:00")])
    assert any("end_time must be after start_time" in e for e in errors)


def test_lunch_start_without_end():
    errors, _ = validate_availability([_entry(lunch_start="12:00")])
    assert any("must both be provided" in e for e in errors)


def test_lunch_end_without_start():
    errors, _ = validate_availability([_entry(lunch_end="13:00")])
    assert any("must both be provided" in e for e in errors)


def test_lunch_outside_window():
    errors, _ = validate_availability([_entry(start="10:00", end="16:00", lunch_start="08:00", lunch_end="09:00")])
    assert any("within the work window" in e for e in errors)


def test_lunch_end_before_lunch_start():
    errors, _ = validate_availability([_entry(lunch_start="13:00", lunch_end="12:00")])
    assert any("lunch_end must be after lunch_start" in e for e in errors)


def test_no_active_day_warning():
    entry = _entry(is_active=False)
    errors, warnings = validate_availability([entry])
    assert errors == []
    assert any("No active day" in w for w in warnings)


def test_empty_list_warning():
    errors, warnings = validate_availability([])
    assert errors == []
    assert any("No active day" in w for w in warnings)


def test_inactive_entries_ignored():
    # Invalid times but is_active=False → no errors
    errors, _ = validate_availability([_entry(start="17:00", end="09:00", is_active=False)])
    assert errors == []


# --- generate_slots ---

def _avail(start="09:00", end="17:00", lunch_start=None, lunch_end=None, is_active=True):
    def t(s):
        h, m = map(int, s.split(":"))
        return time(h, m)

    return {
        "start_time": t(start),
        "end_time": t(end),
        "lunch_start": t(lunch_start) if lunch_start else None,
        "lunch_end": t(lunch_end) if lunch_end else None,
        "is_active": is_active,
    }


TARGET = date(2024, 1, 15)


def test_generate_slots_basic():
    slots = generate_slots(_avail("09:00", "11:00"), 60, TARGET)
    assert len(slots) == 2
    assert slots[0] == datetime(2024, 1, 15, 9, 0)
    assert slots[1] == datetime(2024, 1, 15, 10, 0)


def test_generate_slots_with_lunch():
    # 09:00-17:00, lunch 12:00-13:00, 60min slots
    slots = generate_slots(_avail("09:00", "17:00", "12:00", "13:00"), 60, TARGET)
    starts = [s.hour for s in slots]
    assert 12 not in starts
    assert 9 in starts
    assert 13 in starts
    assert len(slots) == 7  # 9,10,11,13,14,15,16


def test_generate_slots_inactive():
    slots = generate_slots(_avail(is_active=False), 60, TARGET)
    assert slots == []


def test_generate_slots_duration_larger_than_window():
    slots = generate_slots(_avail("09:00", "10:00"), 120, TARGET)
    assert slots == []


def test_generate_slots_30min():
    # 09:00-10:00, 30min → 2 slots
    slots = generate_slots(_avail("09:00", "10:00"), 30, TARGET)
    assert len(slots) == 2


def test_generate_slots_lunch_overlap_skipped():
    # 09:00-14:00, lunch 12:00-13:00, 60min
    # Slots: 9, 10, 11, (12 overlaps), 13
    slots = generate_slots(_avail("09:00", "14:00", "12:00", "13:00"), 60, TARGET)
    hours = [s.hour for s in slots]
    assert 12 not in hours
    assert hours == [9, 10, 11, 13]
