"""Tests for document_pipeline.extraction."""

from __future__ import annotations

import json
from typing import Any

import pytest

from document_pipeline import config
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


class TestChunkedExtraction:
    """Tests for extraction of documents split into multiple chunks."""

    @pytest.fixture(autouse=True)
    def _small_chunk_size(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Force a tiny chunk size so a short test document still splits."""
        monkeypatch.setattr(config, "EXTRACTION_CHUNK_MAX_CHARS", 40)

    def test_long_document_makes_one_call_per_chunk(self) -> None:
        """A document that splits into N chunks should call the client N times."""
        document_text = "\n\n".join(f"Paragraph {i}." + "x" * 30 for i in range(4))
        chunk_responses = [
            json.dumps(
                {
                    "title": "Doc",
                    "metadata": {},
                    "sections": [{"heading": f"Chunk {i}", "content": f"content {i}"}],
                }
            )
            for i in range(4)
        ]
        client = FakeAgentClient(chunk_responses)

        result = extraction_agent(document_text, client=client)

        assert len(client.calls) == 4
        assert [section.heading for section in result.sections] == [
            "Chunk 0",
            "Chunk 1",
            "Chunk 2",
            "Chunk 3",
        ]

    def test_merge_uses_first_chunks_title_and_metadata(self) -> None:
        """The merged document's title/metadata should come from the first chunk only."""
        document_text = "\n\n".join(f"Paragraph {i}." + "x" * 30 for i in range(2))
        chunk_responses = [
            json.dumps(
                {
                    "title": "First Chunk Title",
                    "metadata": {"source": "chunk-0"},
                    "sections": [{"heading": "A", "content": "a"}],
                }
            ),
            json.dumps(
                {
                    "title": "Second Chunk Title",
                    "metadata": {"source": "chunk-1"},
                    "sections": [{"heading": "B", "content": "b"}],
                }
            ),
        ]
        client = FakeAgentClient(chunk_responses)

        result = extraction_agent(document_text, client=client)

        assert result.title == "First Chunk Title"
        assert result.metadata == {"source": "chunk-0"}

    def test_merge_renumbers_auto_generated_section_headings(self) -> None:
        """Each chunk's independently-numbered 'Section N' headings should be
        renumbered sequentially across the merged document, not duplicated."""
        document_text = "\n\n".join(f"Paragraph {i}." + "x" * 30 for i in range(2))
        chunk_responses = [
            json.dumps(
                {
                    "title": "Doc",
                    "metadata": {},
                    "sections": [
                        {"heading": "Section 1", "content": "chunk0 sec1"},
                        {"heading": "Section 2", "content": "chunk0 sec2"},
                    ],
                }
            ),
            json.dumps(
                {
                    "title": "Doc",
                    "metadata": {},
                    "sections": [{"heading": "Section 1", "content": "chunk1 sec1"}],
                }
            ),
        ]
        client = FakeAgentClient(chunk_responses)

        result = extraction_agent(document_text, client=client)

        assert [section.heading for section in result.sections] == [
            "Section 1",
            "Section 2",
            "Section 3",
        ]
        assert result.sections[2].content == "chunk1 sec1"

    def test_real_section_headings_are_left_untouched(self) -> None:
        """Genuine (non-auto-generated) headings should pass through unchanged."""
        document_text = "\n\n".join(f"Paragraph {i}." + "x" * 30 for i in range(2))
        chunk_responses = [
            json.dumps(
                {
                    "title": "Doc",
                    "metadata": {},
                    "sections": [{"heading": "Introduction", "content": "intro"}],
                }
            ),
            json.dumps(
                {
                    "title": "Doc",
                    "metadata": {},
                    "sections": [{"heading": "Section 1", "content": "auto"}],
                }
            ),
        ]
        client = FakeAgentClient(chunk_responses)

        result = extraction_agent(document_text, client=client)

        assert [section.heading for section in result.sections] == ["Introduction", "Section 1"]

    def test_chunk_user_message_mentions_part_position(self) -> None:
        """Each chunk's user message should say which part it is, out of how many."""
        document_text = "\n\n".join(f"Paragraph {i}." + "x" * 30 for i in range(2))
        chunk_responses = [
            json.dumps({"title": "Doc", "metadata": {}, "sections": [{"heading": "A", "content": "a"}]}),
            json.dumps({"title": "Doc", "metadata": {}, "sections": [{"heading": "B", "content": "b"}]}),
        ]
        client = FakeAgentClient(chunk_responses)

        extraction_agent(document_text, client=client)

        _, first_message, _ = client.calls[0]
        _, second_message, _ = client.calls[1]
        assert "part 1 of 2" in first_message
        assert "part 2 of 2" in second_message
