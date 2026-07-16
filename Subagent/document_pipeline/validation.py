"""Schema validation for the Extraction and Analysis agents' JSON output.

These functions operate on plain dicts (the parsed JSON, before it is
converted into a dataclass) so they can be unit-tested in isolation and
reused both inside each agent and by the orchestrator, per the pipeline
specification's explicit validation steps.
"""

from __future__ import annotations

from typing import Any

from document_pipeline import config
from document_pipeline.models import AnalysisValidationError, ExtractionValidationError


def validate_extraction_output(data: dict[str, Any]) -> None:
    """Validate the Extraction Agent's parsed JSON against its required schema.

    Args:
        data: The parsed JSON object returned by the Extraction Agent.

    Raises:
        ExtractionValidationError: If ``title`` is missing or not a non-empty
            string, ``metadata`` is not a dict, ``sections`` is not a list,
            or any section is missing ``heading``/``content``.
    """
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ExtractionValidationError(
            "Extraction output must contain a non-empty string 'title'."
        )

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        raise ExtractionValidationError("Extraction output's 'metadata' must be a dict.")

    sections = data.get("sections")
    if not isinstance(sections, list):
        raise ExtractionValidationError("Extraction output's 'sections' must be a list.")

    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            raise ExtractionValidationError(f"Section at index {index} must be an object.")
        if "heading" not in section or "content" not in section:
            raise ExtractionValidationError(
                f"Section at index {index} must have 'heading' and 'content' keys."
            )


def validate_analysis_output(data: dict[str, Any]) -> None:
    """Validate the Analysis Agent's parsed JSON against its required schema.

    Args:
        data: The parsed JSON object returned by the Analysis Agent.

    Raises:
        AnalysisValidationError: If ``claims``, ``entities``, or ``topics``
            is not a list, or if any item's confidence score is missing or
            outside [``config.MIN_CONFIDENCE``, ``config.MAX_CONFIDENCE``].
    """
    for list_name in ("claims", "entities", "topics"):
        items = data.get(list_name)
        if not isinstance(items, list):
            raise AnalysisValidationError(f"Analysis output's '{list_name}' must be a list.")
        for index, item in enumerate(items):
            _validate_confidence(item, list_name, index)


def _validate_confidence(item: Any, list_name: str, index: int) -> None:
    """Validate a single claim/entity/topic item's confidence score.

    Args:
        item: The item to validate.
        list_name: Name of the containing list, for error messages.
        index: The item's index within its list, for error messages.

    Raises:
        AnalysisValidationError: If the item isn't an object, has no
            ``confidence`` key, or its confidence is out of bounds.
    """
    if not isinstance(item, dict):
        raise AnalysisValidationError(f"{list_name}[{index}] must be an object.")

    confidence = item.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise AnalysisValidationError(f"{list_name}[{index}] must have a numeric 'confidence'.")

    if not (config.MIN_CONFIDENCE <= confidence <= config.MAX_CONFIDENCE):
        raise AnalysisValidationError(
            f"{list_name}[{index}]'s confidence {confidence} is outside "
            f"[{config.MIN_CONFIDENCE}, {config.MAX_CONFIDENCE}]."
        )
