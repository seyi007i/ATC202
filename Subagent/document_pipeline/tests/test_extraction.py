"""Tests for document_pipeline.extraction."""

from __future__ import annotations

from typing import Any

import pytest

from document_pipeline.extraction import extraction_agent
from document_pipeline.models import (
    AnthropicAPIError,
    AnthropicTimeoutError,
    DocumentExtractionFailedError,
    ExtractionValidationError,
    MalformedAgentOutputError,
)
from document_pipeline.prompts import EXTRACTION_SYSTEM_PROMPT
from document_pipeline.tests.conftest import FakeAgentClient


def test_happy_path_returns_extracted_document(valid_extraction_json: str) -> None:
    """A well-formed response should be parsed into an ExtractedDocument."""
    client = FakeAgentClient(valid_extraction_json)

    result = extraction_agent("Some document text.", client=client)

    assert result.title == "Renewable Energy Policy"
    assert len(result.sections) == 2
    system_prompt, user_message, _ = client.calls[0]
    assert system_prompt == EXTRACTION_SYSTEM_PROMPT
    assert "Some document text." in user_message


def test_handles_markdown_fenced_json(valid_extraction_dict: dict[str, Any]) -> None:
    """A response wrapped in a markdown code fence should still parse."""
    import json

    fenced = f"```json\n{json.dumps(valid_extraction_dict)}\n```"
    client = FakeAgentClient(fenced)

    result = extraction_agent("Some document text.", client=client)

    assert result.title == valid_extraction_dict["title"]


def test_malformed_json_propagates() -> None:
    """A response that isn't parseable JSON should raise."""
    client = FakeAgentClient("not json at all")

    with pytest.raises(MalformedAgentOutputError):
        extraction_agent("Some document text.", client=client)


def test_schema_invalid_json_raises_extraction_validation_error() -> None:
    """A parseable but schema-invalid response should raise."""
    client = FakeAgentClient('{"title": "", "metadata": {}, "sections": []}')

    with pytest.raises(ExtractionValidationError):
        extraction_agent("Some document text.", client=client)


def test_api_error_propagates() -> None:
    """An Anthropic API error should propagate unchanged."""
    client = FakeAgentClient(error=AnthropicAPIError("boom"))

    with pytest.raises(AnthropicAPIError):
        extraction_agent("Some document text.", client=client)


def test_timeout_error_propagates() -> None:
    """An Anthropic timeout should propagate unchanged."""
    client = FakeAgentClient(error=AnthropicTimeoutError("timed out"))

    with pytest.raises(AnthropicTimeoutError):
        extraction_agent("Some document text.", client=client)


def test_empty_text_raises_without_calling_client() -> None:
    """Empty document text should raise before any API call is made."""
    client = FakeAgentClient("should not be used")

    with pytest.raises(DocumentExtractionFailedError):
        extraction_agent("   ", client=client)

    assert client.calls == []
