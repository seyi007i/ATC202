"""Tests for document_pipeline.json_utils."""

from __future__ import annotations

import pytest

from document_pipeline.json_utils import extract_json_object
from document_pipeline.models import MalformedAgentOutputError


def test_parses_clean_json() -> None:
    """Plain, unwrapped JSON should parse directly."""
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_parses_json_wrapped_in_json_fence() -> None:
    """A ```json fenced code block should be unwrapped and parsed."""
    text = '```json\n{"a": 1}\n```'
    assert extract_json_object(text) == {"a": 1}


def test_parses_json_wrapped_in_bare_fence() -> None:
    """A bare ``` fenced code block (no language tag) should also parse."""
    text = '```\n{"a": 1}\n```'
    assert extract_json_object(text) == {"a": 1}


def test_parses_json_with_leading_and_trailing_prose() -> None:
    """JSON preceded/followed by stray prose should still be recovered."""
    text = 'Here is the JSON:\n{"a": 1}\nLet me know if that helps!'
    assert extract_json_object(text) == {"a": 1}


def test_garbage_text_raises_malformed_agent_output_error() -> None:
    """Text with no recoverable JSON object should raise."""
    with pytest.raises(MalformedAgentOutputError):
        extract_json_object("I cannot help with that request.")


def test_top_level_json_array_raises_malformed_agent_output_error() -> None:
    """A bare JSON array (not an object) should be rejected."""
    with pytest.raises(MalformedAgentOutputError):
        extract_json_object("[1, 2, 3]")


def test_empty_string_raises_malformed_agent_output_error() -> None:
    """An empty response should raise, not crash with an unrelated error."""
    with pytest.raises(MalformedAgentOutputError):
        extract_json_object("")
