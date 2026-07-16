"""The Extraction Agent: converts raw document text into structured JSON.

The Extraction Agent's only responsibility is preserving document structure
(title, metadata, sections). It must not summarize, analyze, or otherwise
interpret the content — see :data:`document_pipeline.prompts.EXTRACTION_SYSTEM_PROMPT`.
"""

from __future__ import annotations

from document_pipeline import config, validation
from document_pipeline.anthropic_client import AnthropicAgentClient
from document_pipeline.json_utils import extract_json_object
from document_pipeline.models import DocumentExtractionFailedError, ExtractedDocument
from document_pipeline.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_user_message


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
        AnthropicTimeoutError: If the request to the Anthropic API times out.
        AnthropicAPIError: If the Anthropic API returns an error.
        MalformedAgentOutputError: If the response cannot be parsed as JSON.
        ExtractionValidationError: If the parsed JSON fails schema validation.
    """
    if not document_text.strip():
        raise DocumentExtractionFailedError("Cannot extract structure from empty document text.")

    agent_client = client if client is not None else AnthropicAgentClient()
    raw_response = agent_client.complete(
        EXTRACTION_SYSTEM_PROMPT,
        build_extraction_user_message(document_text),
        max_tokens=config.EXTRACTION_MAX_TOKENS,
    )

    data = extract_json_object(raw_response)
    validation.validate_extraction_output(data)
    return ExtractedDocument.from_dict(data)
