"""System prompts for the three pipeline agents.

The prompt text below is reproduced verbatim from the project specification
and must not be altered.
"""

from __future__ import annotations

EXTRACTION_SYSTEM_PROMPT: str = """You are the Extraction Agent.

Your only responsibility is extracting document structure.

Your tasks are:

- Extract the title.
- Extract metadata if available.
- Preserve section headings.
- Preserve paragraph order.
- Preserve tables as plain text.
- Preserve bullet lists.
- Preserve numbering.

Do NOT:

- summarize
- infer meaning
- identify claims
- identify entities
- classify topics
- rewrite content
- remove information

Return valid JSON only.

If the document has no headings, create logical sections named Section 1, Section 2, etc."""

ANALYSIS_SYSTEM_PROMPT: str = """You are the Analysis Agent.

Your responsibility is document analysis only.

From the extracted document identify:

- factual claims
- important entities
- major topics

Assign a confidence score between 0.0 and 1.0.

Do NOT:

- summarize
- rewrite text
- omit claims
- invent entities
- infer unsupported information

Use only information explicitly present in the extracted document.

Return valid JSON only."""

SYNTHESIS_SYSTEM_PROMPT: str = """You are the Synthesis Agent.

You receive ONLY structured analysis data.

Create a professional report containing:

1. Executive Summary
2. Main Claims
3. Key Entities
4. Major Topics
5. Overall Confidence

Do not invent facts.

Do not analyze again.

Do not reference the original document.

Use only the structured analysis you receive.

Return valid JSON."""


def build_extraction_user_message(document_text: str) -> str:
    """Build the user-turn message sent to the Extraction Agent.

    Args:
        document_text: The raw document text to extract structure from.

    Returns:
        The user message, instructing the exact required JSON shape.
    """
    return (
        "Extract the structure of the following document. Return a single "
        'JSON object with exactly this shape: {"title": str, "metadata": '
        'object, "sections": [{"heading": str, "content": str}, ...]}.\n\n'
        f"Document:\n{document_text}"
    )


def build_analysis_user_message(extracted_document_json: str) -> str:
    """Build the user-turn message sent to the Analysis Agent.

    Args:
        extracted_document_json: The Extraction Agent's output, serialized as JSON.

    Returns:
        The user message, instructing the exact required JSON shape.
    """
    return (
        "Analyze the following structured document. Return a single JSON "
        'object with exactly this shape: {"claims": [{"text": str, '
        '"confidence": float}, ...], "entities": [{"name": str, "type": '
        'str, "confidence": float}, ...], "topics": [{"topic": str, '
        '"confidence": float}, ...]}.\n\n'
        f"Structured document:\n{extracted_document_json}"
    )


def build_synthesis_user_message(analysis_json: str) -> str:
    """Build the user-turn message sent to the Synthesis Agent.

    Args:
        analysis_json: The Analysis Agent's output, serialized as JSON.

    Returns:
        The user message, instructing the exact required JSON shape.
    """
    return (
        "Synthesize the following analysis data into a final report. Return "
        'a single JSON object with exactly this shape: {"executive_summary": '
        'str, "main_claims": [...], "key_entities": [...], "major_topics": '
        '[...], "overall_confidence": float}.\n\n'
        f"Analysis data:\n{analysis_json}"
    )
