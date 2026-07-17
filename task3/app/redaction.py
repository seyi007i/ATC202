"""Scrub sensitive banking secrets out of user text before storage or send.

SafeBank Companion must never retain or forward passwords, PINs, OTPs,
BVNs, or full account numbers. ``redact_sensitive`` is applied to every
user message before it is stored in conversation history or sent to the
Anthropic API, so raw secrets never persist or leave the machine.
"""

from __future__ import annotations

import re

_REDACTED = "[REDACTED]"
_REDACTED_BVN_LIKE = "[REDACTED-BVN-LIKE]"
_REDACTED_ACCOUNT_LIKE = "[REDACTED-ACCOUNT-LIKE]"

# "My OTP is 123456", "PIN: 4321", "password=Secret123", "bvn = 12345678901"
# The captured value is only redacted if it contains a digit (see
# _redact_labeled_secret below) — otherwise phrases like "OTP is meant to..."
# or "password is required" would be mistaken for an actual secret value.
_LABELED_SECRET = re.compile(
    r"(?i)\b(otp|pin|bvn|password|passcode|cvv)\b(\s*(?:is|:|=)\s*)([A-Za-z0-9]{3,20})"
)

# "the otp 123456" / "code 4321" with no explicit separator
_KEYWORD_NEARBY_DIGITS = re.compile(
    r"(?i)\b(otp|pin|code)\b[^\d\n]{0,10}(\d{4,8})\b"
)

# Nigerian BVN-shaped bare 11-digit number (also matches phone numbers;
# redacted conservatively since both are sensitive identifiers)
_BARE_11_DIGITS = re.compile(r"(?<!\d)\d{11}(?!\d)")

# Nigerian NUBAN-shaped bare 10-digit account number
_BARE_10_DIGITS = re.compile(r"(?<!\d)\d{10}(?!\d)")


def _redact_labeled_secret(match: re.Match[str]) -> str:
    """Redact the matched value only if it looks like an actual code.

    Real OTPs/PINs/BVNs/CVVs are always digits, and most real passwords
    contain at least one digit. Requiring a digit avoids mistaking plain
    English (e.g. "OTP is meant to...", "password is required") for a
    leaked secret.
    """
    keyword, separator, value = match.group(1), match.group(2), match.group(3)
    if any(char.isdigit() for char in value):
        return f"{keyword}{separator}{_REDACTED}"
    return match.group(0)


def redact_sensitive(text: str) -> str:
    """Redact OTPs, PINs, BVNs, passwords, and full account numbers.

    Args:
        text: Raw user-supplied text.

    Returns:
        The text with sensitive values replaced by redaction markers.
        Running this function again on already-redacted text is a no-op.
    """
    result = _LABELED_SECRET.sub(_redact_labeled_secret, text)
    result = _KEYWORD_NEARBY_DIGITS.sub(rf"\1 {_REDACTED}", result)
    result = _BARE_11_DIGITS.sub(_REDACTED_BVN_LIKE, result)
    result = _BARE_10_DIGITS.sub(_REDACTED_ACCOUNT_LIKE, result)
    return result
