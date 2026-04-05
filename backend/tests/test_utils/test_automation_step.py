import pytest
from app.core.utils.automation_step import resolve_variables


BASE_CONTEXT = {
    "prenom": "Alice",
    "nom": "Dupont",
    "email": "alice@example.com",
    "telephone": "+33612345678",
    "date_rdv": "2024-01-20 10:00",
    "calendrier": "Mon Calendrier",
}


def test_basic_replacement():
    result = resolve_variables("Bonjour {prenom} {nom}", BASE_CONTEXT, "booking_confirme")
    assert result == "Bonjour Alice Dupont"


def test_all_variables_replaced():
    content = "{prenom} {nom} {email} {telephone} {date_rdv} {calendrier}"
    result = resolve_variables(content, BASE_CONTEXT, "booking_confirme")
    assert "Alice" in result
    assert "Dupont" in result
    assert "alice@example.com" in result
    assert "+33612345678" in result
    assert "2024-01-20 10:00" in result
    assert "Mon Calendrier" in result


def test_date_rdv_na_for_coordonnees_trigger():
    result = resolve_variables("RDV: {date_rdv}", BASE_CONTEXT, "coordonnees_sans_booking")
    assert "N/A" in result


def test_date_rdv_na_when_context_none():
    ctx = {**BASE_CONTEXT, "date_rdv": None}
    result = resolve_variables("RDV: {date_rdv}", ctx, "booking_confirme")
    assert "N/A" in result


def test_date_rdv_present_in_normal_trigger():
    result = resolve_variables("RDV: {date_rdv}", BASE_CONTEXT, "avant_rdv")
    assert "2024-01-20 10:00" in result
    assert "N/A" not in result


def test_unknown_variable_left_unchanged():
    result = resolve_variables("Hello {unknown_var}", BASE_CONTEXT, "booking_confirme")
    assert "{unknown_var}" in result


def test_no_variables():
    result = resolve_variables("Bonjour, merci de votre confiance.", BASE_CONTEXT, "booking_confirme")
    assert result == "Bonjour, merci de votre confiance."


def test_empty_content():
    result = resolve_variables("", BASE_CONTEXT, "booking_confirme")
    assert result == ""


def test_multiple_whitespace_collapsed():
    content = "{prenom}  {nom}"
    result = resolve_variables(content, BASE_CONTEXT, "booking_confirme")
    # After replacement: "Alice  Dupont" → collapsed to "Alice Dupont"
    assert "  " not in result
    assert "Alice Dupont" == result


def test_missing_context_key_not_replaced():
    ctx = {k: v for k, v in BASE_CONTEXT.items() if k != "telephone"}
    result = resolve_variables("Tel: {telephone}", ctx, "booking_confirme")
    assert "{telephone}" in result


def test_trim_leading_trailing_whitespace():
    result = resolve_variables("  hello  ", BASE_CONTEXT, "booking_confirme")
    assert result == "hello"
