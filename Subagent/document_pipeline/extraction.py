"""The Extraction Agent: converts raw document text into structured JSON.

The Extraction Agent's only responsibility is preserving document structure
(title, metadata, sections). It must not summarize, analyze, or otherwise
interpret the content — see :data:`document_pipeline.prompts.EXTRACTION_SYSTEM_PROMPT`.

Documents longer than :data:`document_pipeline.config.EXTRACTION_CHUNK_MAX_CHARS`
are split into chunks (see :mod:`document_pipeline.chunking`), extracted one
chunk at a time, and merged back into a single :class:`ExtractedDocument` -
this keeps every individual Anthropic call's echoed-verbatim JSON output
comfortably within a non-streaming call's token budget.
"""

from __future__ import annotations

import re

from document_pipeline import config, validation
from document_pipeline.anthropic_client import AnthropicAgentClient
from document_pipeline.chunking import split_into_chunks
from document_pipeline.json_utils import extract_json_object
from document_pipeline.models import (
    DocumentExtractionFailedError,
    ExtractedDocument,
    ExtractedSection,
)
from document_pipeline.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_user_message

_AUTO_SECTION_HEADING_RE = re.compile(r"^Section \d+$")


def extraction_agent(
    document_text: str, *, client: AnthropicAgentClient | None = None
) -> ExtractedDocument:
    """Run the Extraction Agent on raw document text.

    Args:
        document_text: The raw text of the document to extract structure from.
        client: An optional :class:`AnthropicAgentClient` to use instead of a
            real one, for dependency injection in tests.

    Returns:
        The extracted document's structure.

    Raises:
        DocumentExtractionFailedError: If ``document_text`` is empty or
            whitespace-only.
        AnthropicTimeoutError: If a request to the Anthropic API times out.
        AnthropicAPIError: If the Anthropic API returns an error.
        MalformedAgentOutputError: If a response cannot be parsed as JSON.
        ExtractionValidationError: If a chunk's parsed JSON fails schema validation.
    """
    if not document_text.strip():
        raise DocumentExtractionFailedError("Cannot extract structure from empty document text.")

    agent_client = client if client is not None else AnthropicAgentClient()
    chunks = split_into_chunks(document_text, config.EXTRACTION_CHUNK_MAX_CHARS)

    chunk_documents = [
        _extract_chunk(chunk, index, len(chunks), client=agent_client)
        for index, chunk in enumerate(chunks)
    ]
    return _merge_chunk_documents(chunk_documents)


def _extract_chunk(
    chunk_text: str, part_index: int, part_count: int, *, client: AnthropicAgentClient
) -> ExtractedDocument:
    """Run the Extraction Agent on a single chunk of document text.

    Args:
        chunk_text: The chunk's raw text.
        part_index: The zero-based index of this chunk.
        part_count: The total number of chunks the document was split into.
        client: The client to send this chunk's extraction call through.

    Returns:
        The extracted structure of this chunk alone.
    """
    raw_response = client.complete(
        EXTRACTION_SYSTEM_PROMPT,
        build_extraction_user_message(chunk_text, part_index=part_index, part_count=part_count),
        max_tokens=config.EXTRACTION_MAX_TOKENS,
    )
    data = extract_json_object(raw_response)
    validation.validate_extraction_output(data)
    return ExtractedDocument.from_dict(data)


def _merge_chunk_documents(chunk_documents: list[ExtractedDocument]) -> ExtractedDocument:
    """Merge per-chunk extraction results into a single ExtractedDocument.

    The title and metadata are taken from the first chunk only. Sections
    from every chunk are concatenated in order. Auto-generated headings
    (``"Section 1"``, ``"Section 2"``, ...) are renumbered sequentially
    across the merged document, since each chunk numbers its own
    auto-generated sections independently and would otherwise collide.

    Args:
        chunk_documents: One ExtractedDocument per chunk, in chunk order.

    Returns:
        The merged ExtractedDocument.
    """
    first = chunk_documents[0]
    merged_sections: list[ExtractedSection] = []
    auto_section_count = 0

    for document in chunk_documents:
        for section in document.sections:
            if _AUTO_SECTION_HEADING_RE.match(section.heading):
                auto_section_count += 1
                merged_sections.append(
                    ExtractedSection(heading=f"Section {auto_section_count}", content=section.content)
                )
            else:
                merged_sections.append(section)

    return ExtractedDocument(title=first.title, metadata=first.metadata, sections=tuple(merged_sections))
