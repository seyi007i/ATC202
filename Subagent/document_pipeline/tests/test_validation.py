"""Tests for document_pipeline.validation."""

from __future__ import annotations

from typing import Any

import pytest

from document_pipeline.models import AnalysisValidationError, ExtractionValidationError
from document_pipeline.validation import validate_analysis_output, validate_extraction_output


class TestValidateExtractionOutput:
    """Tests for validate_extraction_output."""

    def test_valid_dict_passes(self, valid_extraction_dict: dict[str, Any]) -> None:
        """A well-formed extraction dict should not raise."""
        validate_extraction_output(valid_extraction_dict)

    def test_missing_title_raises(self, valid_extraction_dict: dict[str, Any]) -> None:
        """A missing 'title' key should raise."""
        del valid_extraction_dict["title"]
        with pytest.raises(ExtractionValidationError):
            validate_extraction_output(valid_extraction_dict)

    def test_empty_title_raises(self, valid_extraction_dict: dict[str, Any]) -> None:
        """A blank/whitespace-only 'title' should raise."""
        valid_extraction_dict["title"] = "   "
        with pytest.raises(ExtractionValidationError):
            validate_extraction_output(valid_extraction_dict)

    def test_non_dict_metadata_raises(self, valid_extraction_dict: dict[str, Any]) -> None:
        """A non-dict 'metadata' should raise."""
        valid_extraction_dict["metadata"] = "not a dict"
        with pytest.raises(ExtractionValidationError):
            validate_extraction_output(valid_extraction_dict)

    def test_non_list_sections_raises(self, valid_extraction_dict: dict[str, Any]) -> None:
        """A non-list 'sections' should raise."""
        valid_extraction_dict["sections"] = "not a list"
        with pytest.raises(ExtractionValidationError):
            validate_extraction_output(valid_extraction_dict)

    def test_section_missing_heading_raises(self, valid_extraction_dict: dict[str, Any]) -> None:
        """A section missing 'heading' should raise."""
        valid_extraction_dict["sections"] = [{"content": "no heading here"}]
        with pytest.raises(ExtractionValidationError):
            validate_extraction_output(valid_extraction_dict)

    def test_section_missing_content_raises(self, valid_extraction_dict: dict[str, Any]) -> None:
        """A section missing 'content' should raise."""
        valid_extraction_dict["sections"] = [{"heading": "no content here"}]
        with pytest.raises(ExtractionValidationError):
            validate_extraction_output(valid_extraction_dict)

    def test_non_dict_section_raises(self, valid_extraction_dict: dict[str, Any]) -> None:
        """A section that isn't an object should raise."""
        valid_extraction_dict["sections"] = ["not a dict"]
        with pytest.raises(ExtractionValidationError):
            validate_extraction_output(valid_extraction_dict)


class TestValidateAnalysisOutput:
    """Tests for validate_analysis_output."""

    def test_valid_dict_passes(self, valid_analysis_dict: dict[str, Any]) -> None:
        """A well-formed analysis dict should not raise."""
        validate_analysis_output(valid_analysis_dict)

    @pytest.mark.parametrize("list_name", ["claims", "entities", "topics"])
    def test_non_list_field_raises(self, valid_analysis_dict: dict[str, Any], list_name: str) -> None:
        """Each of claims/entities/topics must be a list."""
        valid_analysis_dict[list_name] = "not a list"
        with pytest.raises(AnalysisValidationError):
            validate_analysis_output(valid_analysis_dict)

    def test_missing_confidence_raises(self, valid_analysis_dict: dict[str, Any]) -> None:
        """An item missing 'confidence' should raise."""
        del valid_analysis_dict["claims"][0]["confidence"]
        with pytest.raises(AnalysisValidationError):
            validate_analysis_output(valid_analysis_dict)

    def test_confidence_above_max_raises(self, valid_analysis_dict: dict[str, Any]) -> None:
        """A confidence score above 1.0 should raise."""
        valid_analysis_dict["claims"][0]["confidence"] = 1.5
        with pytest.raises(AnalysisValidationError):
            validate_analysis_output(valid_analysis_dict)

    def test_confidence_below_min_raises(self, valid_analysis_dict: dict[str, Any]) -> None:
        """A confidence score below 0.0 should raise."""
        valid_analysis_dict["entities"][0]["confidence"] = -0.1
        with pytest.raises(AnalysisValidationError):
            validate_analysis_output(valid_analysis_dict)

    def test_non_numeric_confidence_raises(self, valid_analysis_dict: dict[str, Any]) -> None:
        """A non-numeric confidence value should raise."""
        valid_analysis_dict["topics"][0]["confidence"] = "high"
        with pytest.raises(AnalysisValidationError):
            validate_analysis_output(valid_analysis_dict)

    def test_boundary_confidence_values_accepted(self, valid_analysis_dict: dict[str, Any]) -> None:
        """Confidence values of exactly 0.0 and 1.0 should be accepted."""
        valid_analysis_dict["claims"][0]["confidence"] = 0.0
        valid_analysis_dict["entities"][0]["confidence"] = 1.0
        validate_analysis_output(valid_analysis_dict)

    def test_non_dict_item_raises(self, valid_analysis_dict: dict[str, Any]) -> None:
        """A list item that isn't an object should raise."""
        valid_analysis_dict["claims"] = ["not a dict"]
        with pytest.raises(AnalysisValidationError):
            validate_analysis_output(valid_analysis_dict)
