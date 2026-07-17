"""Splitting long document text into extraction-sized chunks.

The Extraction Agent echoes a chunk's content back verbatim inside JSON, so
a single non-streaming Anthropic call can only handle a bounded amount of
input text before its output would need more tokens than a non-streaming
call safely allows. Long documents are split here, on paragraph boundaries,
into chunks small enough to extract independently; :mod:`document_pipeline.extraction`
merges the resulting per-chunk documents back into one.
"""

from __future__ import annotations


def split_into_chunks(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of at most ``max_chars``, on paragraph boundaries.

    Paragraphs (separated by a blank line) are packed greedily into each
    chunk. A single paragraph longer than ``max_chars`` becomes its own
    (oversized) chunk rather than being cut mid-sentence.

    Args:
        text: The full document text to split.
        max_chars: The target maximum length, in characters, of each chunk.

    Returns:
        A list of one or more chunks. Joining them with blank lines
        reconstructs the original text.
    """
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []

    for paragraph in paragraphs:
        candidate = [*current, paragraph]
        if current and len("\n\n".join(candidate)) > max_chars:
            chunks.append("\n\n".join(current))
            current = [paragraph]
        else:
            current = candidate

    if current:
        chunks.append("\n\n".join(current))

    return chunks or [text]
