"""The Analysis Agent: identifies claims, entities, and topics.

The Analysis Agent's only responsibility is document analysis (claims,
entities, topics with confidence scores) — it must not summarize. See
:data:`document_pipeline.prompts.ANALYSIS_SYSTEM_PROMPT`.
"""

from __future__ import annotations

import json
from typing import Any

from document_pipeline import config, validation
from document_pipeline.anthropic_client import AnthropicAgentClient
from document_pipeline.json_utils import extract_json_object
from document_pipeline.models import AnalysisResult, ExtractedDocument
from document_pipeline.prompts import ANALYSIS_SYSTEM_PROMPT, build_analysis_user_message


def analysis_agent(
    extracted: ExtractedDocument | dict[str, Any], *, client: AnthropicAgentClient | None = None
) -> AnalysisResult:
    """Run the Analysis Agent on a structured (extracted) document.

    Args:
        extracted: The Extraction Agent's output, as an ExtractedDocument or
            its equivalent dict.
        client: An optional :class:`AnthropicAgentClient` to use instead of a
            real one, for dependency injection in tests.

    Returns:
        The identified claims, entities, and topics.

    Raises:
        AnthropicTimeoutError: If the request to the Anthropic API times out.
        AnthropicAPIError: If the Anthropic API returns an error.
        MalformedAgentOutputError: If the response cannot be parsed as JSON.
        AnalysisValidationError: If the parsed JSON fails schema validation.
    """
    extracted_dict = extracted.to_dict() if isinstance(extracted, ExtractedDocument) else extracted

    agent_client = client if client is not None else AnthropicAgentClient()
    raw_response = agent_client.complete(
        ANALYSIS_SYSTEM_PROMPT,
        build_analysis_user_message(json.dumps(extracted_dict)),
        max_tokens=config.ANALYSIS_MAX_TOKENS,
    )

    data = extract_json_object(raw_response)
    validation.validate_analysis_output(data)
    return AnalysisResult.from_dict(data)
