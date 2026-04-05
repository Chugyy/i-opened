import time
import pytest
from app.core.utils.user import (
    hash_password,
    verify_password,
    generate_tokens,
    verify_token,
    TokenExpiredError,
    InvalidTokenError,
)


# --- hash_password / verify_password ---

def test_hash_password_returns_string():
    result = hash_password("secret")
    assert isinstance(result, str)
    assert result != "secret"


def test_hash_password_bcrypt_prefix():
    result = hash_password("secret")
    assert result.startswith("$2")


def test_verify_password_correct():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("mypassword")
    assert verify_password("wrong", hashed) is False


def test_hash_password_different_hashes():
    # Same password → different hashes (bcrypt salts)
    h1 = hash_password("abc")
    h2 = hash_password("abc")
    assert h1 != h2


# --- generate_tokens ---

def test_generate_tokens_returns_both_tokens():
    result = generate_tokens(user_id=1, email="test@example.com")
    assert "access_token" in result
    assert "refresh_token" in result


def test_generate_tokens_are_strings():
    result = generate_tokens(user_id=1, email="test@example.com")
    assert isinstance(result["access_token"], str)
    assert isinstance(result["refresh_token"], str)


def test_generate_tokens_different_tokens():
    result = generate_tokens(user_id=1, email="test@example.com")
    assert result["access_token"] != result["refresh_token"]


# --- verify_token ---

def test_verify_token_access_valid():
    tokens = generate_tokens(user_id=42, email="u@example.com")
    payload = verify_token(tokens["access_token"], expected_type="access")
    assert payload["sub"] == "42"
    assert payload["email"] == "u@example.com"
    assert payload["type"] == "access"


def test_verify_token_refresh_valid():
    tokens = generate_tokens(user_id=42, email="u@example.com")
    payload = verify_token(tokens["refresh_token"], expected_type="refresh")
    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"


def test_verify_token_wrong_type_raises():
    tokens = generate_tokens(user_id=1, email="u@example.com")
    with pytest.raises(InvalidTokenError):
        verify_token(tokens["access_token"], expected_type="refresh")


def test_verify_token_wrong_type_refresh_as_access():
    tokens = generate_tokens(user_id=1, email="u@example.com")
    with pytest.raises(InvalidTokenError):
        verify_token(tokens["refresh_token"], expected_type="access")


def test_verify_token_invalid_string_raises():
    with pytest.raises(InvalidTokenError):
        verify_token("not.a.valid.jwt", expected_type="access")


def test_verify_token_tampered_raises():
    tokens = generate_tokens(user_id=1, email="u@example.com")
    tampered = tokens["access_token"] + "x"
    with pytest.raises(InvalidTokenError):
        verify_token(tampered, expected_type="access")
