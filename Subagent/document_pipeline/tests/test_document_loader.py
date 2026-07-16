"""Tests for document_pipeline.document_loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from document_pipeline.document_loader import load_document_text
from document_pipeline.models import (
    DocumentExtractionFailedError,
    InvalidDocumentPathError,
    UnsupportedDocumentFormatError,
)


def test_loads_txt_file(tmp_txt_file: Path) -> None:
    """A .txt file's text should be read back verbatim."""
    text = load_document_text(tmp_txt_file)
    assert "Sample Document" in text
    assert "test paragraph" in text


def test_loads_md_file(tmp_md_file: Path) -> None:
    """A .md file's text should be read back verbatim."""
    text = load_document_text(tmp_md_file)
    assert "# Sample Document" in text


def test_loads_pdf_file(tmp_pdf_file: Path) -> None:
    """A .pdf file's text should be extracted via pymupdf."""
    text = load_document_text(tmp_pdf_file)
    assert "Sample PDF Document" in text


def test_loads_docx_file(tmp_docx_file: Path) -> None:
    """A .docx file's text should be extracted via python-docx."""
    text = load_document_text(tmp_docx_file)
    assert "Sample DOCX Document" in text


def test_missing_file_raises_invalid_document_path_error(tmp_path: Path) -> None:
    """A nonexistent path should raise InvalidDocumentPathError."""
    with pytest.raises(InvalidDocumentPathError):
        load_document_text(tmp_path / "does_not_exist.txt")


def test_directory_path_raises_invalid_document_path_error(tmp_path: Path) -> None:
    """A directory (not a file) should raise InvalidDocumentPathError."""
    with pytest.raises(InvalidDocumentPathError):
        load_document_text(tmp_path)


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    """An unrecognized extension should raise UnsupportedDocumentFormatError."""
    path = tmp_path / "sample.exe"
    path.write_bytes(b"not a real document")
    with pytest.raises(UnsupportedDocumentFormatError):
        load_document_text(path)


def test_corrupt_pdf_raises_extraction_failed(tmp_path: Path) -> None:
    """A .pdf file that isn't actually a valid PDF should raise."""
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"this is not a pdf")
    with pytest.raises(DocumentExtractionFailedError):
        load_document_text(path)


def test_corrupt_docx_raises_extraction_failed(tmp_path: Path) -> None:
    """A .docx file that isn't actually a valid DOCX should raise."""
    path = tmp_path / "corrupt.docx"
    path.write_bytes(b"this is not a docx")
    with pytest.raises(DocumentExtractionFailedError):
        load_document_text(path)


def test_empty_txt_file_raises_extraction_failed(tmp_path: Path) -> None:
    """A .txt file with only whitespace should raise DocumentExtractionFailedError."""
    path = tmp_path / "empty.txt"
    path.write_text("   \n\n  ", encoding="utf-8")
    with pytest.raises(DocumentExtractionFailedError):
        load_document_text(path)


def test_non_utf8_txt_file_raises_extraction_failed(tmp_path: Path) -> None:
    """A .txt file that isn't valid UTF-8 should raise DocumentExtractionFailedError."""
    path = tmp_path / "invalid_encoding.txt"
    path.write_bytes(b"\xff\xfe\x00invalid utf-8")
    with pytest.raises(DocumentExtractionFailedError):
        load_document_text(path)
