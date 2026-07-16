"""Tests for document_pipeline.synthesis."""

from __future__ import annotations

from typing import Any

import pytest

from document_pipeline.models import (
    AnalysisResult,
    AnthropicAPIError,
    AnthropicTimeoutError,
    MalformedAgentOutputError,
)
from document_pipeline.prompts import SYNTHESIS_SYSTEM_PROMPT
from document_pipeline.synthesis import synthesis_agent
from document_pipeline.tests.conftest import FakeAgentClient


def test_happy_path_accepts_dict_input(
    valid_analysis_dict: dict[str, Any], valid_synthesis_json: str
) -> None:
    """A dict analysis input should produce a valid SynthesisReport."""
    client = FakeAgentClient(valid_synthesis_json)

    result = synthesis_agent(valid_analysis_dict, client=client)

    assert result.executive_summary
    assert result.overall_confidence == 0.96
    system_prompt, _, _ = client.calls[0]
    assert system_prompt == SYNTHESIS_SYSTEM_PROMPT


def test_happy_path_accepts_analysis_result_input(
    valid_analysis_dict: dict[str, Any], valid_synthesis_json: str
) -> None:
    """An AnalysisResult input should produce a valid SynthesisReport."""
    analysis = AnalysisResult.from_dict(valid_analysis_dict)
    client = FakeAgentClient(valid_synthesis_json)

    result = synthesis_agent(analysis, client=client)

    assert result.main_claims


def test_does_not_leak_original_document_fields(
    valid_analysis_dict: dict[str, Any], valid_synthesis_json: str
) -> None:
    """The message sent to the model must contain only analysis data, never
    the original document's title/sections."""
    client = FakeAgentClient(valid_synthesis_json)

    synthesis_agent(valid_analysis_dict, client=client)

    _, user_message, _ = client.calls[0]
    assert "claims" in user_message
    assert "title" not in user_message
    assert "sections" not in user_message


def test_malformed_json_propagates(valid_analysis_dict: dict[str, Any]) -> None:
    """A response that isn't parseable JSON should raise."""
    client = FakeAgentClient("not json at all")

    with pytest.raises(MalformedAgentOutputError):
        synthesis_agent(valid_analysis_dict, client=client)


def test_missing_executive_summary_raises_malformed_agent_output_error(
    valid_analysis_dict: dict[str, Any],
) -> None:
    """A response missing the required executive_summary key should raise."""
    client = FakeAgentClient('{"main_claims": [], "key_entities": [], "major_topics": []}')

    with pytest.raises(MalformedAgentOutputError):
        synthesis_agent(valid_analysis_dict, client=client)


def test_api_error_propagates(valid_analysis_dict: dict[str, Any]) -> None:
    """An Anthropic API error should propagate unchanged."""
    client = FakeAgentClient(error=AnthropicAPIError("boom"))

    with pytest.raises(AnthropicAPIError):
        synthesis_agent(valid_analysis_dict, client=client)


def test_timeout_error_propagates(valid_analysis_dict: dict[str, Any]) -> None:
    """An Anthropic timeout should propagate unchanged."""
    client = FakeAgentClient(error=AnthropicTimeoutError("timed out"))

    with pytest.raises(AnthropicTimeoutError):
        synthesis_agent(valid_analysis_dict, client=client)
