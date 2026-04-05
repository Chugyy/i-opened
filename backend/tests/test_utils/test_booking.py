import pytest
from datetime import datetime
from app.core.utils.booking import compute_available_slots


def dt(h: int, m: int = 0) -> datetime:
    return datetime(2024, 1, 15, h, m)


ALL_SLOTS = [dt(9), dt(10), dt(11), dt(12), dt(13), dt(14), dt(15), dt(16)]


def test_no_conflicts():
    result = compute_available_slots(ALL_SLOTS, [], [], 60)
    assert result == ALL_SLOTS


def test_booking_removes_slot():
    bookings = [{"starts_at": dt(10), "ends_at": dt(11)}]
    result = compute_available_slots(ALL_SLOTS, bookings, [], 60)
    assert dt(10) not in result
    assert dt(9) in result


def test_multiple_bookings():
    bookings = [
        {"starts_at": dt(9), "ends_at": dt(10)},
        {"starts_at": dt(14), "ends_at": dt(15)},
    ]
    result = compute_available_slots(ALL_SLOTS, bookings, [], 60)
    assert dt(9) not in result
    assert dt(14) not in result
    assert dt(10) in result


def test_gcal_event_overlap_removes_slot():
    # Event 09:30-10:30 overlaps with 09:00-10:00 and 10:00-11:00
    gcal_events = [{"start": dt(9, 30), "end": dt(10, 30)}]
    result = compute_available_slots(ALL_SLOTS, [], gcal_events, 60)
    assert dt(9) not in result
    assert dt(10) not in result
    assert dt(11) in result


def test_gcal_event_no_overlap():
    # Event exactly at slot boundary: 10:00-11:00 does NOT overlap with 11:00-12:00
    gcal_events = [{"start": dt(10), "end": dt(11)}]
    result = compute_available_slots(ALL_SLOTS, [], gcal_events, 60)
    assert dt(11) in result
    assert dt(10) not in result


def test_gcal_event_iso_string():
    gcal_events = [{"start": "2024-01-15T09:30:00", "end": "2024-01-15T10:30:00"}]
    result = compute_available_slots(ALL_SLOTS, [], gcal_events, 60)
    assert dt(9) not in result
    assert dt(10) not in result


def test_booking_iso_string():
    bookings = [{"starts_at": "2024-01-15T09:00:00", "ends_at": "2024-01-15T10:00:00"}]
    result = compute_available_slots(ALL_SLOTS, bookings, [], 60)
    assert dt(9) not in result
    assert dt(10) in result


def test_empty_slots():
    result = compute_available_slots([], [], [], 60)
    assert result == []


def test_result_sorted():
    slots = [dt(14), dt(9), dt(11)]
    result = compute_available_slots(slots, [], [], 60)
    assert result == sorted(result)


def test_booking_and_gcal_combined():
    bookings = [{"starts_at": dt(9), "ends_at": dt(10)}]
    gcal_events = [{"start": dt(11, 30), "end": dt(12, 30)}]
    result = compute_available_slots(ALL_SLOTS, bookings, gcal_events, 60)
    assert dt(9) not in result   # booking
    assert dt(11) not in result  # gcal overlap (11:00-12:00 vs 11:30-12:30)
    assert dt(12) not in result  # gcal overlap (12:00-13:00 vs 11:30-12:30)
    assert dt(10) in result
