"""Loading raw text out of supported document file formats.

Supports plain text (.txt, .md), PDF (via pymupdf), and DOCX (via
python-docx). Raw text strings that don't come from a file are handled by
:func:`document_pipeline.orchestrator.process_document_text` instead of here,
since guessing whether a bare string is a path or literal content risks
silently misinterpreting a mistyped path as document content.
"""

from __future__ import annotations

from pathlib import Path

import docx
import fitz

from document_pipeline import config
from document_pipeline.models import (
    DocumentExtractionFailedError,
    InvalidDocumentPathError,
    UnsupportedDocumentFormatError,
)


def load_document_text(document_path: str | Path) -> str:
    """Read a supported document file and return its raw text content.

    Args:
        document_path: Path to a .txt, .md, .pdf, or .docx file.

    Returns:
        The document's extracted text.

    Raises:
        InvalidDocumentPathError: If the path does not exist or is not a file.
        UnsupportedDocumentFormatError: If the file extension is not one of
            ``config.SUPPORTED_EXTENSIONS``.
        DocumentExtractionFailedError: If the file cannot be read/parsed or
            its extracted text is empty.
    """
    path = Path(document_path)
    if not path.is_file():
        raise InvalidDocumentPathError(f"Document path does not exist or is not a file: {path}")

    extension = path.suffix.lower()
    if extension not in config.SUPPORTED_EXTENSIONS:
        raise UnsupportedDocumentFormatError(f"Unsupported document format: {extension!r}")

    readers = {
        ".txt": _read_plain_text,
        ".md": _read_plain_text,
        ".pdf": _read_pdf,
        ".docx": _read_docx,
    }
    text = readers[extension](path)

    if not text.strip():
        raise DocumentExtractionFailedError(f"Extracted text from {path} was empty.")
    return text


def _read_plain_text(path: Path) -> str:
    """Read a .txt or .md file as UTF-8 text.

    Args:
        path: Path to the file.

    Returns:
        The file's text content.

    Raises:
        DocumentExtractionFailedError: If the file cannot be decoded as UTF-8.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DocumentExtractionFailedError(f"Could not decode {path} as UTF-8 text.") from exc


def _read_pdf(path: Path) -> str:
    """Extract text from a PDF file using pymupdf.

    Args:
        path: Path to the PDF file.

    Returns:
        The concatenated text of every page.

    Raises:
        DocumentExtractionFailedError: If the PDF cannot be opened or read.
    """
    try:
        with fitz.open(path) as document:
            return "\n".join(page.get_text() for page in document)
    except Exception as exc:  # noqa: BLE001 - pymupdf raises varied error types
        raise DocumentExtractionFailedError(f"Could not extract text from PDF {path}: {exc}") from exc


def _read_docx(path: Path) -> str:
    """Extract text from a DOCX file using python-docx.

    Args:
        path: Path to the DOCX file.

    Returns:
        The concatenated text of every paragraph.

    Raises:
        DocumentExtractionFailedError: If the DOCX cannot be opened or read.
    """
    try:
        document = docx.Document(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:  # noqa: BLE001 - python-docx raises varied error types
        raise DocumentExtractionFailedError(f"Could not extract text from DOCX {path}: {exc}") from exc
