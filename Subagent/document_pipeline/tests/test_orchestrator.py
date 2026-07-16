"""Tests for document_pipeline.orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from document_pipeline.models import (
    ExtractionValidationError,
    InvalidDocumentPathError,
    MalformedAgentOutputError,
    UnsupportedDocumentFormatError,
)
from document_pipeline.orchestrator import process_document, process_document_text
from document_pipeline.tests.conftest import FakeAgentClient


def test_end_to_end_happy_path(
    tmp_txt_file: Path,
    valid_extraction_json: str,
    valid_analysis_json: str,
    valid_synthesis_json: str,
) -> None:
    """A full run should call all three agents in order and return the report."""
    client = FakeAgentClient([valid_extraction_json, valid_analysis_json, valid_synthesis_json])

    report = process_document(str(tmp_txt_file), client=client)

    assert report["executive_summary"]
    assert report["overall_confidence"] == 0.96
    assert len(client.calls) == 3


def test_missing_file_propagates(tmp_path: Path) -> None:
    """A missing document path should raise InvalidDocumentPathError."""
    client = FakeAgentClient([])

    with pytest.raises(InvalidDocumentPathError):
        process_document(str(tmp_path / "missing.txt"), client=client)

    assert client.calls == []


def test_unsupported_extension_propagates(tmp_path: Path) -> None:
    """An unsupported file extension should raise UnsupportedDocumentFormatError."""
    path = tmp_path / "sample.exe"
    path.write_bytes(b"not a document")
    client = FakeAgentClient([])

    with pytest.raises(UnsupportedDocumentFormatError):
        process_document(str(path), client=client)


def test_malformed_json_at_extraction_stage_propagates_unwrapped(tmp_txt_file: Path) -> None:
    """A malformed extraction response should propagate as itself, not RuntimeError."""
    client = FakeAgentClient(["not valid json"])

    with pytest.raises(MalformedAgentOutputError):
        process_document(str(tmp_txt_file), client=client)


def test_schema_invalid_extraction_propagates_unwrapped(tmp_txt_file: Path) -> None:
    """A schema-invalid extraction response should propagate as itself."""
    client = FakeAgentClient(['{"title": "", "metadata": {}, "sections": []}'])

    with pytest.raises(ExtractionValidationError):
        process_document(str(tmp_txt_file), client=client)


def test_unexpected_exception_wrapped_in_runtime_error(tmp_txt_file: Path) -> None:
    """A genuinely unexpected exception should be wrapped in RuntimeError."""
    client = FakeAgentClient(error=ValueError("something truly unexpected"))

    with pytest.raises(RuntimeError) as exc_info:
        process_document(str(tmp_txt_file), client=client)

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_process_document_text_known_error_propagates_unwrapped() -> None:
    """A known pipeline error should propagate as itself, not RuntimeError."""
    client = FakeAgentClient(["not valid json"])

    with pytest.raises(MalformedAgentOutputError):
        process_document_text("Some raw document text.", client=client)


def test_process_document_text_unexpected_exception_wrapped_in_runtime_error() -> None:
    """A genuinely unexpected exception should be wrapped in RuntimeError."""
    client = FakeAgentClient(error=ValueError("something truly unexpected"))

    with pytest.raises(RuntimeError) as exc_info:
        process_document_text("Some raw document text.", client=client)

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_process_document_text_happy_path_parity(
    valid_extraction_json: str, valid_analysis_json: str, valid_synthesis_json: str
) -> None:
    """process_document_text should behave like process_document, minus file I/O."""
    client = FakeAgentClient([valid_extraction_json, valid_analysis_json, valid_synthesis_json])

    report = process_document_text("Some raw document text.", client=client)

    assert report["executive_summary"]
    assert len(client.calls) == 3
