import pytest
from app.core.utils.calendar import generate_slug


def test_simple_name():
    assert generate_slug("Mon Calendrier", []) == "mon-calendrier"


def test_accents_removed():
    assert generate_slug("Réunion Générale", []) == "reunion-generale"


def test_special_chars_replaced():
    assert generate_slug("Mon Calendrier Pro!", []) == "mon-calendrier-pro"


def test_multiple_spaces_collapsed():
    assert generate_slug("hello   world", []) == "hello-world"


def test_truncated_at_60_chars():
    long_name = "a" * 70
    result = generate_slug(long_name, [])
    assert len(result) <= 60


def test_no_conflict():
    result = generate_slug("test", [])
    assert result == "test"


def test_conflict_adds_suffix_2():
    result = generate_slug("test", ["test"])
    assert result == "test-2"


def test_conflict_adds_suffix_3():
    result = generate_slug("test", ["test", "test-2"])
    assert result == "test-3"


def test_conflict_multiple():
    existing = ["test", "test-2", "test-3", "test-4"]
    result = generate_slug("test", existing)
    assert result == "test-5"


def test_empty_name_fallback():
    result = generate_slug("!!!", [])
    assert result == "calendrier"


def test_uppercase_normalized():
    assert generate_slug("HELLO WORLD", []) == "hello-world"


def test_mixed_content():
    assert generate_slug("  My Cal -- 2024  ", []) == "my-cal-2024"
