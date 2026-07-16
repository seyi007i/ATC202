"""Shared fixtures for document_pipeline tests.

Every test in this suite injects a :class:`FakeAgentClient` instead of a real
:class:`~document_pipeline.anthropic_client.AnthropicAgentClient`, so the
suite makes zero real network calls.
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

import docx
import fitz
import pytest

from document_pipeline.models import DocumentPipelineError


class FakeAgentClient:
    """A duck-typed stand-in for AnthropicAgentClient.

    Attributes:
        calls: Every (system_prompt, user_message, max_tokens) tuple passed
            to ``complete``, in call order.
    """

    def __init__(
        self,
        responses: str | list[str] | None = None,
        *,
        error: DocumentPipelineError | None = None,
    ) -> None:
        """Initialize the fake client.

        Args:
            responses: A single response string, or a list of response
                strings to return in FIFO order across successive calls.
            error: If given, every call raises this exception instead of
                returning a response.
        """
        self._error = error
        if responses is None:
            self._responses: deque[str] = deque()
        elif isinstance(responses, str):
            self._responses = deque([responses])
        else:
            self._responses = deque(responses)
        self.calls: list[tuple[str, str, int]] = []

    def complete(self, system_prompt: str, user_message: str, *, max_tokens: int) -> str:
        """Record the call and return the next queued response.

        Args:
            system_prompt: The system prompt passed by the caller.
            user_message: The user message passed by the caller.
            max_tokens: The max_tokens value passed by the caller.

        Returns:
            The next queued response string.

        Raises:
            DocumentPipelineError: The configured ``error``, if any.
        """
        self.calls.append((system_prompt, user_message, max_tokens))
        if self._error is not None:
            raise self._error
        return self._responses.popleft()


@pytest.fixture
def valid_extraction_dict() -> dict[str, Any]:
    """A schema-valid Extraction Agent output dict."""
    return {
        "title": "Renewable Energy Policy",
        "metadata": {"pages": 3, "language": "English"},
        "sections": [
            {"heading": "Introduction", "content": "This document discusses renewable energy."},
            {"heading": "Methods", "content": "Government incentives were analyzed."},
        ],
    }


@pytest.fixture
def valid_extraction_json(valid_extraction_dict: dict[str, Any]) -> str:
    """A schema-valid Extraction Agent output, serialized as JSON text."""
    return json.dumps(valid_extraction_dict)


@pytest.fixture
def valid_analysis_dict() -> dict[str, Any]:
    """A schema-valid Analysis Agent output dict."""
    return {
        "claims": [{"text": "Government incentives increased solar adoption.", "confidence": 0.95}],
        "entities": [{"name": "Department of Energy", "type": "Organization", "confidence": 0.98}],
        "topics": [{"topic": "Renewable Energy", "confidence": 0.97}],
    }


@pytest.fixture
def valid_analysis_json(valid_analysis_dict: dict[str, Any]) -> str:
    """A schema-valid Analysis Agent output, serialized as JSON text."""
    return json.dumps(valid_analysis_dict)


@pytest.fixture
def valid_synthesis_dict() -> dict[str, Any]:
    """A schema-valid Synthesis Agent output dict."""
    return {
        "executive_summary": "The document discusses renewable energy policy.",
        "main_claims": ["Government incentives increased solar adoption."],
        "key_entities": ["Department of Energy"],
        "major_topics": ["Renewable Energy"],
        "overall_confidence": 0.96,
    }


@pytest.fixture
def valid_synthesis_json(valid_synthesis_dict: dict[str, Any]) -> str:
    """A schema-valid Synthesis Agent output, serialized as JSON text."""
    return json.dumps(valid_synthesis_dict)


@pytest.fixture
def tmp_txt_file(tmp_path: Path) -> Path:
    """A .txt file containing simple sample text."""
    path = tmp_path / "sample.txt"
    path.write_text("Sample Document\n\nThis is a test paragraph.", encoding="utf-8")
    return path


@pytest.fixture
def tmp_md_file(tmp_path: Path) -> Path:
    """A .md file containing simple sample text."""
    path = tmp_path / "sample.md"
    path.write_text("# Sample Document\n\nThis is a test paragraph.", encoding="utf-8")
    return path


@pytest.fixture
def tmp_pdf_file(tmp_path: Path) -> Path:
    """A real, minimal .pdf file built at test time via pymupdf."""
    path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Sample PDF Document")
    document.save(path)
    document.close()
    return path


@pytest.fixture
def tmp_docx_file(tmp_path: Path) -> Path:
    """A real, minimal .docx file built at test time via python-docx."""
    path = tmp_path / "sample.docx"
    document = docx.Document()
    document.add_paragraph("Sample DOCX Document")
    document.save(path)
    return path
