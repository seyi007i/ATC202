"""Tests for app.redaction.redact_sensitive."""

from __future__ import annotations

from app.redaction import redact_sensitive


def test_redacts_labeled_otp():
    text = "My OTP is 123456, please help."
    result = redact_sensitive(text)
    assert "123456" not in result
    assert "[REDACTED]" in result


def test_redacts_labeled_pin():
    text = "PIN: 4321"
    result = redact_sensitive(text)
    assert "4321" not in result
    assert "[REDACTED]" in result


def test_redacts_labeled_password():
    text = "password=Secret123"
    result = redact_sensitive(text)
    assert "Secret123" not in result
    assert "[REDACTED]" in result


def test_redacts_otp_without_explicit_separator():
    text = "the otp 987654 was sent to me"
    result = redact_sensitive(text)
    assert "987654" not in result


def test_redacts_bare_11_digit_bvn_like_number():
    text = "My BVN number is 12345678901 if you need it."
    result = redact_sensitive(text)
    assert "12345678901" not in result
    assert "[REDACTED-BVN-LIKE]" in result


def test_redacts_bare_10_digit_account_like_number():
    text = "Send it to account 0123456789 please."
    result = redact_sensitive(text)
    assert "0123456789" not in result
    assert "[REDACTED-ACCOUNT-LIKE]" in result


def test_legitimate_text_untouched():
    text = "Is my account safe? I got a strange message today."
    result = redact_sensitive(text)
    assert result == text


def test_redaction_is_idempotent():
    text = "My OTP is 123456 and my BVN is 12345678901."
    once = redact_sensitive(text)
    twice = redact_sensitive(once)
    assert once == twice


def test_short_numbers_not_over_redacted():
    text = "I have 5 transactions and lost NGN 200 today."
    result = redact_sensitive(text)
    assert result == text


def test_explanatory_sentences_about_otp_are_not_mangled():
    text = "An OTP is meant only to be entered by you, never shared with anyone."
    result = redact_sensitive(text)
    assert result == text


def test_explanatory_sentences_about_password_are_not_mangled():
    text = "Your password is required to log in, but never share it with anyone."
    result = redact_sensitive(text)
    assert result == text
