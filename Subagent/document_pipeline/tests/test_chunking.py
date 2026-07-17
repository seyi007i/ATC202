"""Tests for document_pipeline.chunking."""

from __future__ import annotations

from document_pipeline.chunking import split_into_chunks


def test_short_text_returns_single_chunk() -> None:
    """Text well under max_chars should come back as one chunk, unchanged."""
    text = "Paragraph one.\n\nParagraph two."
    assert split_into_chunks(text, max_chars=1000) == [text]


def test_splits_on_paragraph_boundaries() -> None:
    """Text over max_chars should split between paragraphs, not mid-paragraph."""
    paragraphs = [f"Paragraph {i} " + "x" * 20 for i in range(5)]
    text = "\n\n".join(paragraphs)

    chunks = split_into_chunks(text, max_chars=60)

    assert len(chunks) > 1
    assert "".join(chunks).count("Paragraph 0") == 1
    assert "".join(chunks).count("Paragraph 4") == 1
    for chunk in chunks:
        assert len(chunk) <= 60


def test_reconstructs_original_text() -> None:
    """Joining the chunks back together should reproduce the original text."""
    paragraphs = [f"Paragraph {i}." for i in range(6)]
    text = "\n\n".join(paragraphs)

    chunks = split_into_chunks(text, max_chars=25)

    assert "\n\n".join(chunks) == text


def test_oversized_single_paragraph_becomes_its_own_chunk() -> None:
    """A paragraph longer than max_chars should not be cut mid-sentence."""
    long_paragraph = "word " * 100
    text = f"Short paragraph.\n\n{long_paragraph}\n\nAnother short one."

    chunks = split_into_chunks(text, max_chars=50)

    assert long_paragraph in chunks


def test_empty_text_returns_single_empty_chunk() -> None:
    """Empty input should return a single (empty) chunk, not an empty list."""
    assert split_into_chunks("", max_chars=100) == [""]
