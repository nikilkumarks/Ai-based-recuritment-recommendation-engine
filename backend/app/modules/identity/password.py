"""Argon2id password hashing and validation. Never store or log plaintext passwords."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.errors import UnprocessableError

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# Obviously weak passwords. Not an exhaustive denylist.
COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password12",
        "password123",
        "12345678",
        "123456789",
        "qwerty123",
        "letmein1",
        "letmein12",
        "welcome1",
        "admin123",
        "passw0rd",
    }
)


def _hasher() -> PasswordHasher:
    settings = get_settings()
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=2,
    )


def hash_password(plain: str) -> str:
    return _hasher().hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return _hasher().verify(password_hash, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def dummy_password_hash() -> str:
    """Used to keep login timing closer when the email does not exist."""
    return hash_password("dummy-password-not-used-for-authentication")


_DUMMY_HASH: str | None = None


def consume_password_check(plain: str, password_hash: str | None) -> bool:
    """Verify against the real hash, or against a dummy hash if the account is missing."""
    global _DUMMY_HASH
    if password_hash is None:
        if _DUMMY_HASH is None:
            _DUMMY_HASH = dummy_password_hash()
        verify_password(plain, _DUMMY_HASH)
        return False
    return verify_password(plain, password_hash)


def validate_password(password: str, email: str) -> None:
    if password != password.strip():
        raise UnprocessableError("Password must not start or end with whitespace.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise UnprocessableError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise UnprocessableError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")
    if password.lower() == email.strip().lower():
        raise UnprocessableError("Password must not be the same as the email address.")
    if len(set(password)) == 1:
        raise UnprocessableError("Password is too weak.")
    if password.lower() in COMMON_PASSWORDS:
        raise UnprocessableError("Password is too common.")
