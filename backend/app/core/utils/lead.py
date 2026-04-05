import re

_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*"
    r"\.[a-zA-Z]{2,}$"
)
_PHONE_E164_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")


def validate_contact(email: str, phone: str) -> tuple[bool, list[str]]:
    """
    Validate email format (RFC 5321) and phone E.164 format.
    Returns (is_valid, errors). All errors are collected before returning.
    """
    errors: list[str] = []

    if not _EMAIL_REGEX.match(email):
        errors.append("Format email invalide")

    if not _PHONE_E164_REGEX.match(phone):
        errors.append("Format E.164 requis (ex: +33612345678)")

    return len(errors) == 0, errors
