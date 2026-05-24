"""personadiary waitlist API validation (no Next server)."""

from __future__ import annotations


def _validate(email: str) -> str | None:
    if not email or not str(email).strip():
        return "email_required"
    if "@" not in email:
        return "email_invalid"
    return None


def test_validate_ok() -> None:
    assert _validate("a@b.co") is None


def test_validate_required() -> None:
    assert _validate("") == "email_required"


def test_validate_invalid() -> None:
    assert _validate("not-an-email") == "email_invalid"
