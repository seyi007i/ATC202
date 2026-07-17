"""Reusable helper functions shared across the Student Support Assistant.

Includes input validation, lightweight text processing, student-ID
extraction, and logging setup. Keeping these here avoids duplicating
validation logic between :mod:`tools` and :mod:`agent`.
"""

from __future__ import annotations

import logging
import re

from student_support_assistance import config
from student_support_assistance.models import EmptyQueryError, InvalidInputError, Intent

_WORD_PATTERN: re.Pattern[str] = re.compile(r"[a-z0-9]+")


def setup_logging(level: int = config.LOG_LEVEL) -> logging.Logger:
    """Configure and return the application's shared logger.

    Safe to call multiple times: it only attaches a handler the first
    time, so repeated calls (e.g. from tests) don't duplicate log lines.

    Args:
        level: Logging level to apply to the logger, e.g. ``logging.INFO``.

    Returns:
        The configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(config.LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def tokenize(text: str) -> set[str]:
    """Split text into a set of lowercase alphanumeric tokens.

    Args:
        text: The text to tokenize.

    Returns:
        A set of lowercase word/number tokens with punctuation removed.
    """
    return set(_WORD_PATTERN.findall(text.lower()))


def require_non_empty_string(value: object, field_name: str) -> str:
    """Validate that ``value`` is a non-blank string.

    Args:
        value: The candidate value to validate.
        field_name: Name of the field, used in error messages.

    Returns:
        The stripped string value.

    Raises:
        InvalidInputError: If ``value`` is not a string.
        EmptyQueryError: If ``value`` is a string but empty/whitespace-only.
    """
    if not isinstance(value, str):
        raise InvalidInputError(
            f"'{field_name}' must be a string, got {type(value).__name__}."
        )
    stripped = value.strip()
    if not stripped:
        raise EmptyQueryError(f"'{field_name}' must not be empty.")
    return stripped


def extract_student_id(text: str) -> str | None:
    """Opportunistically find a student ID pattern within free text.

    Args:
        text: Free-text user message that may reference a student ID.

    Returns:
        The first matching student ID in uppercase, or ``None`` if no
        pattern is found.
    """
    match = config.STUDENT_ID_SEARCH_PATTERN.search(text)
    return match.group(0).upper() if match else None


def classify_intent(text: str) -> Intent:
    """Classify a user message into one of the agent's supported intents.

    Uses simple, deterministic keyword matching rather than a model call so
    the routing behavior is fast, free, and fully testable offline.
    Escalation keywords take priority over enrollment keywords, which take
    priority over the knowledge-base fallback, so a message like "I want to
    appeal my enrollment status" is escalated rather than looked up.

    Args:
        text: The raw user message.

    Returns:
        The :class:`~student_support_assistance.models.Intent` the message
        most likely expresses.
    """
    lowered = text.lower()
    if any(keyword in lowered for keyword in config.ESCALATION_KEYWORDS):
        return Intent.ESCALATION
    if any(keyword in lowered for keyword in config.ENROLLMENT_KEYWORDS):
        return Intent.ENROLLMENT
    return Intent.KNOWLEDGE_BASE
