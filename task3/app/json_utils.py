"""Tolerant JSON extraction from Claude's free-text responses.

Claude sometimes wraps JSON in prose, fenced code blocks, or adds
trailing commentary. ``extract_json_object`` tries progressively looser
strategies before giving up.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.models import MalformedAgentOutputError

_FENCE_PATTERN = re.compile(
    r"```(?:[a-zA-Z0-9_-]*)\s*\n(.*?)```",
    re.DOTALL,
)

_SNIPPET_LIMIT = 500


def extract_json_object(text: str, *, fence_tag: str | None = None) -> dict[str, Any]:
    """Extract the first JSON object embedded in ``text``.

    Tries, in order: parsing ``text`` directly as JSON, extracting a
    fenced code block (optionally requiring a specific ``fence_tag``,
    e.g. ``safebank-assessment``), and finally taking the substring
    between the first ``{`` and the last ``}``.

    Args:
        text: Raw text possibly containing a JSON object.
        fence_tag: If given, only fenced blocks opened with
            ```` ```<fence_tag> ```` are considered before falling back
            to the brace-substring strategy.

    Returns:
        The parsed JSON object as a dict.

    Raises:
        MalformedAgentOutputError: If no valid JSON object can be found.
    """
    stripped = text.strip()

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    if fence_tag:
        tagged_pattern = re.compile(
            r"```" + re.escape(fence_tag) + r"\s*\n(.*?)```", re.DOTALL
        )
        match = tagged_pattern.search(text)
        if match:
            candidate = match.group(1).strip()
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    else:
        for match in _FENCE_PATTERN.finditer(text):
            candidate = match.group(1).strip()
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    snippet = text[:_SNIPPET_LIMIT]
    raise MalformedAgentOutputError(
        f"Could not extract a JSON object from the model's response. "
        f"Snippet: {snippet!r}"
    )
