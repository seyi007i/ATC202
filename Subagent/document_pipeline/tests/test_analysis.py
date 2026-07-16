"""Tests for document_pipeline.analysis."""

from __future__ import annotations

from typing import Any

import pytest

from document_pipeline.analysis import analysis_agent
from document_pipeline.models import (
    AnalysisValidationError,
    AnthropicAPIError,
    AnthropicTimeoutError,
    ExtractedDocument,
    MalformedAgentOutputError,
)
from document_pipeline.prompts import ANALYSIS_SYSTEM_PROMPT
from document_pipeline.tests.conftest import FakeAgentClient


def test_happy_path_accepts_dict_input(
    valid_extraction_dict: dict[str, Any], valid_analysis_json: str
) -> None:
    """A dict extraction input should produce a valid AnalysisResult."""
    client = FakeAgentClient(valid_analysis_json)

    result = analysis_agent(valid_extraction_dict, client=client)

    assert len(result.claims) == 1
    assert result.entities[0].name == "Department of Energy"
    system_prompt, _, _ = client.calls[0]
    assert system_prompt == ANALYSIS_SYSTEM_PROMPT


def test_happy_path_accepts_extracted_document_input(
    valid_extraction_dict: dict[str, Any], valid_analysis_json: str
) -> None:
    """An ExtractedDocument input should produce a valid AnalysisResult."""
    extracted = ExtractedDocument.from_dict(valid_extraction_dict)
    client = FakeAgentClient(valid_analysis_json)

    result = analysis_agent(extracted, client=client)

    assert len(result.topics) == 1


def test_malformed_json_propagates(valid_extraction_dict: dict[str, Any]) -> None:
    """A response that isn't parseable JSON should raise."""
    client = FakeAgentClient("not json at all")

    with pytest.raises(MalformedAgentOutputError):
        analysis_agent(valid_extraction_dict, client=client)


def test_confidence_out_of_bounds_raises(valid_extraction_dict: dict[str, Any]) -> None:
    """An out-of-bounds confidence score should raise AnalysisValidationError."""
    client = FakeAgentClient('{"claims": [{"text": "x", "confidence": 5.0}], "entities": [], "topics": []}')

    with pytest.raises(AnalysisValidationError):
        analysis_agent(valid_extraction_dict, client=client)


def test_api_error_propagates(valid_extraction_dict: dict[str, Any]) -> None:
    """An Anthropic API error should propagate unchanged."""
    client = FakeAgentClient(error=AnthropicAPIError("boom"))

    with pytest.raises(AnthropicAPIError):
        analysis_agent(valid_extraction_dict, client=client)


def test_timeout_error_propagates(valid_extraction_dict: dict[str, Any]) -> None:
    """An Anthropic timeout should propagate unchanged."""
    client = FakeAgentClient(error=AnthropicTimeoutError("timed out"))

    with pytest.raises(AnthropicTimeoutError):
        analysis_agent(valid_extraction_dict, client=client)
