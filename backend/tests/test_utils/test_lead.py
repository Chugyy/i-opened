import pytest
from app.core.utils.lead import validate_contact


# --- Valid cases ---

def test_valid_email_and_phone():
    ok, errors = validate_contact("user@example.com", "+33612345678")
    assert ok is True
    assert errors == []


def test_valid_international_phone():
    ok, errors = validate_contact("a@b.com", "+12025551234")
    assert ok is True


def test_valid_email_with_dots():
    ok, errors = validate_contact("first.last@sub.domain.com", "+33612345678")
    assert ok is True


def test_valid_phone_max_length():
    ok, errors = validate_contact("a@b.com", "+1" + "2" * 13)  # +1 + 13 digits = 15 chars total
    assert ok is True


# --- Invalid email ---

def test_invalid_email_no_at():
    ok, errors = validate_contact("notanemail", "+33612345678")
    assert ok is False
    assert any("email" in e.lower() for e in errors)


def test_invalid_email_no_domain():
    ok, errors = validate_contact("user@", "+33612345678")
    assert ok is False


def test_invalid_email_empty():
    ok, errors = validate_contact("", "+33612345678")
    assert ok is False


def test_invalid_email_spaces():
    ok, errors = validate_contact("user @example.com", "+33612345678")
    assert ok is False


# --- Invalid phone ---

def test_invalid_phone_no_plus():
    ok, errors = validate_contact("user@example.com", "0612345678")
    assert ok is False
    assert any("E.164" in e for e in errors)


def test_invalid_phone_empty():
    ok, errors = validate_contact("user@example.com", "")
    assert ok is False


def test_invalid_phone_too_short():
    # E.164 requires 8-15 digits after +
    ok, errors = validate_contact("user@example.com", "+123")
    assert ok is False


def test_invalid_phone_starts_with_plus_zero():
    # +0... is not valid E.164 (first digit after + must be 1-9)
    ok, errors = validate_contact("user@example.com", "+0612345678")
    assert ok is False


def test_invalid_phone_contains_letters():
    ok, errors = validate_contact("user@example.com", "+336abc45678")
    assert ok is False


# --- Both invalid ---

def test_both_invalid_returns_two_errors():
    ok, errors = validate_contact("notvalid", "notvalid")
    assert ok is False
    assert len(errors) == 2


# --- All errors collected ---

def test_all_errors_collected_not_just_first():
    ok, errors = validate_contact("bad", "bad")
    assert ok is False
    assert len(errors) == 2  # both email and phone errors returned
