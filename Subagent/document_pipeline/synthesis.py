"""The Synthesis Agent: produces the final report from analysis data only.

The Synthesis Agent never sees the original document or the Extraction
Agent's output — its function signature accepts only an analysis result, so
there is no argument through which a caller could pass the source document.
See :data:`document_pipeline.prompts.SYNTHESIS_SYSTEM_PROMPT`.
"""

from __future__ import annotations

import json
from typing import Any

from document_pipeline import config
from document_pipeline.anthropic_client import AnthropicAgentClient
from document_pipeline.json_utils import extract_json_object
from document_pipeline.models import AnalysisResult, MalformedAgentOutputError, SynthesisReport
from document_pipeline.prompts import SYNTHESIS_SYSTEM_PROMPT, build_synthesis_user_message


def synthesis_agent(
    analysis: AnalysisResult | dict[str, Any], *, client: AnthropicAgentClient | None = None
) -> SynthesisReport:
    """Run the Synthesis Agent on an analysis result.

    Args:
        analysis: The Analysis Agent's output, as an AnalysisResult or its
            equivalent dict. This is the only document-derived data the
            Synthesis Agent ever receives.
        client: An optional :class:`AnthropicAgentClient` to use instead of a
            real one, for dependency injection in tests.

    Returns:
        The final synthesized report.

    Raises:
        AnthropicTimeoutError: If the request to the Anthropic API times out.
        AnthropicAPIError: If the Anthropic API returns an error.
        MalformedAgentOutputError: If the response cannot be parsed as JSON,
            or is missing its required ``executive_summary`` field.
    """
    analysis_dict = analysis.to_dict() if isinstance(analysis, AnalysisResult) else analysis

    agent_client = client if client is not None else AnthropicAgentClient()
    raw_response = agent_client.complete(
        SYNTHESIS_SYSTEM_PROMPT,
        build_synthesis_user_message(json.dumps(analysis_dict)),
        max_tokens=config.SYNTHESIS_MAX_TOKENS,
    )

    data = extract_json_object(raw_response)
    try:
        return SynthesisReport.from_dict(data)
    except KeyError as exc:
        raise MalformedAgentOutputError(f"Synthesis output is missing required key: {exc}") from exc
