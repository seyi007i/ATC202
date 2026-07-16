"""Robust JSON extraction from LLM text responses.

Agents are instructed to "return valid JSON only", but models sometimes wrap
their output in markdown code fences or add stray prose despite that
instruction. This module recovers the intended JSON object on a best-effort
basis before giving up.
"""

from __future__ import annotations

import json
import re
from typing import Any

from document_pipeline.models import MalformedAgentOutputError

_FENCE_RE: re.Pattern[str] = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

#: Number of characters of the offending text to include in error messages.
_SNIPPET_LENGTH: int = 500


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object out of an LLM response, tolerating common wrapping.

    Tries, in order: (1) ``json.loads`` on the raw text, (2) the first fenced
    code block (` ```json ... ``` ` or ` ``` ... ``` `), (3) the substring
    between the first ``{`` and the last ``}`` in the text.

    Args:
        text: Raw text returned by the model.

    Returns:
        The parsed JSON object as a dict.

    Raises:
        MalformedAgentOutputError: If no strategy yields a valid, dict-shaped
            JSON object.
    """
    for candidate in _candidates(text):
        parsed = _try_parse_object(candidate)
        if parsed is not None:
            return parsed

    snippet = text[:_SNIPPET_LENGTH]
    raise MalformedAgentOutputError(
        f"Could not parse a JSON object from the agent's response. "
        f"Response began with: {snippet!r}"
    )


def _candidates(text: str) -> list[str]:
    """Build the ordered list of substrings worth attempting to parse.

    Args:
        text: Raw text returned by the model.

    Returns:
        Candidate substrings, most-likely-correct first.
    """
    candidates = [text]

    fence_match = _FENCE_RE.search(text)
    if fence_match:
        candidates.append(fence_match.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    return candidates


def _try_parse_object(candidate: str) -> dict[str, Any] | None:
    """Attempt to parse a candidate string as a JSON object.

    Args:
        candidate: The text to attempt to parse.

    Returns:
        The parsed dict, or ``None`` if parsing failed or produced a
        non-dict value.
    """
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
