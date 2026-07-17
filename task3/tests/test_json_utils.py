"""Tests for app.json_utils.extract_json_object."""

from __future__ import annotations

import pytest

from app.json_utils import extract_json_object
from app.models import MalformedAgentOutputError


def test_extracts_raw_json():
    result = extract_json_object('{"risk_level": "low"}')
    assert result == {"risk_level": "low"}


def test_extracts_fenced_json_block():
    text = 'Here is the result:\n```json\n{"risk_level": "high"}\n```\nDone.'
    result = extract_json_object(text)
    assert result == {"risk_level": "high"}


def test_extracts_tagged_fenced_block_with_fence_tag():
    text = 'Some reply.\n```safebank-assessment\n{"risk_level": "medium"}\n```'
    result = extract_json_object(text, fence_tag="safebank-assessment")
    assert result == {"risk_level": "medium"}


def test_ignores_untagged_fence_when_fence_tag_required_but_falls_back_to_braces():
    text = 'Some reply {"risk_level": "medium"} and no fenced block at all.'
    result = extract_json_object(text, fence_tag="safebank-assessment")
    assert result == {"risk_level": "medium"}


def test_extracts_brace_substring_fallback():
    text = 'The model said: {"risk_level": "low", "flags": []} -- end of message.'
    result = extract_json_object(text)
    assert result == {"risk_level": "low", "flags": []}


def test_raises_on_unparsable_text():
    with pytest.raises(MalformedAgentOutputError, match="Could not extract"):
        extract_json_object("This has no JSON in it whatsoever.")


def test_error_includes_snippet_of_original_text():
    long_text = "no json here " * 100
    with pytest.raises(MalformedAgentOutputError) as exc_info:
        extract_json_object(long_text)
    assert "no json here" in str(exc_info.value)
