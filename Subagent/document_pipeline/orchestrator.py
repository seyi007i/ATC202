"""Orchestrates the full Extraction -> Analysis -> Synthesis pipeline."""

from __future__ import annotations

import sys
from typing import Any

from document_pipeline import validation
from document_pipeline.analysis import analysis_agent
from document_pipeline.anthropic_client import AnthropicAgentClient
from document_pipeline.document_loader import load_document_text
from document_pipeline.extraction import extraction_agent
from document_pipeline.models import DocumentPipelineError
from document_pipeline.synthesis import synthesis_agent
from document_pipeline.utils import setup_logging

logger = setup_logging()


def process_document(document_path: str, *, client: AnthropicAgentClient | None = None) -> dict[str, Any]:
    """Process a document file through the multi-agent pipeline.

    Workflow:
        1. Read the input document from disk.
        2. Call the Extraction Agent.
        3. Validate the extraction output.
        4. Call the Analysis Agent.
        5. Validate the analysis output.
        6. Call the Synthesis Agent.
        7. Return the final structured report.

    Args:
        document_path: Path to a supported document (.txt, .md, .pdf, .docx).
        client: An optional :class:`AnthropicAgentClient` to use instead of a
            real one, for dependency injection in tests.

    Returns:
        A dictionary containing the synthesized report.

    Raises:
        InvalidDocumentPathError: If the document does not exist.
        UnsupportedDocumentFormatError: If the document's format is unsupported.
        DocumentExtractionFailedError: If the document's text can't be read.
        AnthropicAPIError: If any agent's call to the Anthropic API fails.
        AnthropicTimeoutError: If any agent's call to the Anthropic API times out.
        MalformedAgentOutputError: If any agent's response isn't valid JSON.
        ExtractionValidationError: If the extraction output fails validation.
        AnalysisValidationError: If the analysis output fails validation.
        RuntimeError: If an unexpected exception occurs.
    """
    try:
        document_text = load_document_text(document_path)
        return _run_pipeline(document_text, client=client)
    except DocumentPipelineError:
        raise
    except Exception as exc:  # noqa: BLE001 - final safety net, per spec
        logger.exception("Unexpected error while processing document %s: %s", document_path, exc)
        raise RuntimeError(f"Unexpected error while processing document: {exc}") from exc


def process_document_text(document_text: str, *, client: AnthropicAgentClient | None = None) -> dict[str, Any]:
    """Process raw document text through the multi-agent pipeline.

    Identical to :func:`process_document`, but skips file I/O entirely for
    callers that already have the document's text in memory.

    Args:
        document_text: The raw text of the document to process.
        client: An optional :class:`AnthropicAgentClient` to use instead of a
            real one, for dependency injection in tests.

    Returns:
        A dictionary containing the synthesized report.

    Raises:
        DocumentExtractionFailedError: If ``document_text`` is empty.
        AnthropicAPIError: If any agent's call to the Anthropic API fails.
        AnthropicTimeoutError: If any agent's call to the Anthropic API times out.
        MalformedAgentOutputError: If any agent's response isn't valid JSON.
        ExtractionValidationError: If the extraction output fails validation.
        AnalysisValidationError: If the analysis output fails validation.
        RuntimeError: If an unexpected exception occurs.
    """
    try:
        return _run_pipeline(document_text, client=client)
    except DocumentPipelineError:
        raise
    except Exception as exc:  # noqa: BLE001 - final safety net, per spec
        logger.exception("Unexpected error while processing document text: %s", exc)
        raise RuntimeError(f"Unexpected error while processing document: {exc}") from exc


def _run_pipeline(document_text: str, *, client: AnthropicAgentClient | None) -> dict[str, Any]:
    """Run the extraction/analysis/synthesis stages shared by both entry points.

    Args:
        document_text: The raw text of the document to process.
        client: An optional :class:`AnthropicAgentClient` shared across all
            three agent calls.

    Returns:
        A dictionary containing the synthesized report.
    """
    agent_client = client if client is not None else AnthropicAgentClient()

    extraction_output = extraction_agent(document_text, client=agent_client)
    validation.validate_extraction_output(extraction_output.to_dict())

    analysis_output = analysis_agent(extraction_output, client=agent_client)
    validation.validate_analysis_output(analysis_output.to_dict())

    final_report = synthesis_agent(analysis_output, client=agent_client)
    return final_report.to_dict()


def _run_demo(document_path: str) -> None:
    """Print the final report JSON for a document, for ``python -m`` usage.

    Args:
        document_path: Path to the document to process.
    """
    import json

    report = process_document(document_path)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m document_pipeline.orchestrator <document_path>")
        sys.exit(1)
    _run_demo(sys.argv[1])
