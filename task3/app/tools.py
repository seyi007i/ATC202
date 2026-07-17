"""The single callable tool exposed to Claude: fraud_red_flag_check.

The tool is a deterministic, regex/keyword-based heuristic (no LLM
call) so it is fast, free, and fully unit-testable. Claude decides when
to invoke it via real Anthropic tool-use blocks.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from app.models import ToolExecutionError

FRAUD_RED_FLAG_TOOL_SCHEMA: dict[str, Any] = {
    "name": "fraud_red_flag_check",
    "description": (
        "Analyze a suspicious SMS, email, or WhatsApp message for Nigerian "
        "mobile-money fraud red flags: OTP requests, PIN requests, BVN "
        "requests, password requests, suspicious URLs, fake urgency, "
        "threats, account-suspension scams, prize scams, and fake customer "
        "support. Call this whenever the user shares or describes a "
        "suspicious message that has not already been analyzed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The full text of the suspicious message.",
            },
        },
        "required": ["message"],
    },
}

_CRITICAL_FLAGS = frozenset(
    {"requests_otp", "requests_pin", "requests_bvn", "requests_password"}
)

_REQUEST_VERBS = (
    "send",
    "share",
    "provide",
    "enter",
    "confirm",
    "reply with",
    "reply",
    "give",
    "tell us",
    "input",
    "verify",
)

_URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
_SHORTENER_DOMAINS = ("bit.ly", "tinyurl.com", "goo.gl", "is.gd", "t.co", "cutt.ly", "rebrand.ly")
_URL_ACTION_WORDS = ("click", "verify", "update", "confirm", "login", "log in", "reactivate", "unlock")

_URGENCY_KEYWORDS = (
    "urgent",
    "immediately",
    "act now",
    "within 24 hours",
    "within 1 hour",
    "expire",
    "last warning",
    "asap",
    "right away",
    "final notice",
)

_THREAT_KEYWORDS = (
    "arrest",
    "legal action",
    "penalty",
    "prosecute",
    "police",
    "court",
    "fined",
)

_ACCOUNT_SUSPENSION_KEYWORDS = (
    "account will be suspended",
    "account has been suspended",
    "account is suspended",
    "account blocked",
    "account has been blocked",
    "deactivate your account",
    "suspend your account",
    "account will be deactivated",
    "account will be locked",
)

_PRIZE_KEYWORDS = (
    "you have won",
    "you've won",
    "congratulations you",
    "lottery",
    "claim your reward",
    "claim your prize",
    "selected as a winner",
    "you are the winner",
)

_SUPPORT_KEYWORDS = ("customer support", "customer care", "help desk", "support team")
_SUPPORT_ACTION_WORDS = ("verify", "confirm", "provide", "send", "update")


def _has_request_for(text: str, subject_pattern: str) -> bool:
    """Return True if ``text`` mentions ``subject_pattern`` near a request verb."""
    if not re.search(subject_pattern, text):
        return False
    return any(verb in text for verb in _REQUEST_VERBS)


def _requests_otp(text: str) -> bool:
    return _has_request_for(text, r"\botp\b|one[- ]time (password|pin|code)")


def _requests_pin(text: str) -> bool:
    return _has_request_for(text, r"\bpin\b")


def _requests_bvn(text: str) -> bool:
    return _has_request_for(text, r"\bbvn\b")


def _requests_password(text: str) -> bool:
    return _has_request_for(text, r"\bpassword\b|\bpasscode\b")


def _suspicious_url(text: str) -> bool:
    urls = _URL_PATTERN.findall(text)
    if not urls:
        return False
    for url in urls:
        lowered = url.lower()
        if any(domain in lowered for domain in _SHORTENER_DOMAINS):
            return True
        if lowered.startswith("http://"):
            return True
    return any(word in text for word in _URL_ACTION_WORDS)


def _urgency_language(text: str) -> bool:
    return any(keyword in text for keyword in _URGENCY_KEYWORDS)


def _threat_language(text: str) -> bool:
    return any(keyword in text for keyword in _THREAT_KEYWORDS)


def _account_suspension_scam(text: str) -> bool:
    return any(keyword in text for keyword in _ACCOUNT_SUSPENSION_KEYWORDS)


def _prize_scam(text: str) -> bool:
    return any(keyword in text for keyword in _PRIZE_KEYWORDS)


def _fake_customer_support(text: str) -> bool:
    if not any(keyword in text for keyword in _SUPPORT_KEYWORDS):
        return False
    return any(word in text for word in _SUPPORT_ACTION_WORDS)


_DETECTORS: tuple[tuple[str, Callable[[str], bool]], ...] = (
    ("requests_otp", _requests_otp),
    ("requests_pin", _requests_pin),
    ("requests_bvn", _requests_bvn),
    ("requests_password", _requests_password),
    ("suspicious_url", _suspicious_url),
    ("urgency_language", _urgency_language),
    ("threat_language", _threat_language),
    ("account_suspension_scam", _account_suspension_scam),
    ("prize_scam", _prize_scam),
    ("fake_customer_support", _fake_customer_support),
)

_RECOMMENDATIONS = {
    "high": (
        "Do not click any links or share any codes. Contact your bank using "
        "the number on the back of your card or its official app, not any "
        "number or link in this message. Block and report the sender."
    ),
    "medium": (
        "Treat this message with caution. Do not click links or share "
        "personal or account details. Verify by contacting your bank "
        "directly through its official channels before doing anything."
    ),
    "low": (
        "No strong fraud indicators were found, but stay cautious with any "
        "message asking you to click links or share personal information."
    ),
}


def fraud_red_flag_check(message: str) -> dict[str, Any]:
    """Analyze a message for mobile-money fraud red flags.

    Args:
        message: The suspicious message text to analyze.

    Returns:
        A dict with ``risk_level`` ("low"/"medium"/"high"), ``flags``
        (list of detected red-flag identifiers), and ``recommendation``
        (a short safety recommendation).

    Raises:
        ToolExecutionError: If ``message`` is not a non-empty string.
    """
    if not isinstance(message, str) or not message.strip():
        raise ToolExecutionError("fraud_red_flag_check requires a non-empty 'message' string.")

    text = message.lower()
    flags = [name for name, detector in _DETECTORS if detector(text)]

    critical_count = sum(1 for flag in flags if flag in _CRITICAL_FLAGS)
    other_count = len(flags) - critical_count

    if critical_count >= 1 or other_count >= 2:
        risk_level = "high"
    elif other_count == 1:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "flags": flags,
        "recommendation": _RECOMMENDATIONS[risk_level],
    }


TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "fraud_red_flag_check": fraud_red_flag_check,
}


def dispatch_tool_call(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool call requested by Claude.

    Args:
        name: The tool name Claude requested.
        tool_input: The tool's input arguments as provided by Claude.

    Returns:
        The tool's result dict.

    Raises:
        ToolExecutionError: If the tool is unknown or the input is invalid.
    """
    if name not in TOOL_REGISTRY:
        raise ToolExecutionError(f"Unknown tool requested: {name!r}")

    if not isinstance(tool_input, dict) or "message" not in tool_input:
        raise ToolExecutionError("Tool input must be an object with a 'message' field.")

    return TOOL_REGISTRY[name](tool_input["message"])
