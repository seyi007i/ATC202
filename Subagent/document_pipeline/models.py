"""Data contracts and structured exceptions for the document pipeline.

All cross-module data shapes live here as immutable dataclasses, and every
pipeline-specific failure mode has its own exception class rooted at
:class:`DocumentPipelineError`, so callers can catch expected failures
separately from genuine bugs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class DocumentPipelineError(Exception):
    """Base class for all document-pipeline-specific errors."""


class InvalidDocumentPathError(DocumentPipelineError):
    """Raised when a document path does not exist or is not a file."""


class UnsupportedDocumentFormatError(DocumentPipelineError):
    """Raised when a document's file extension is not supported."""


class DocumentExtractionFailedError(DocumentPipelineError):
    """Raised when a supported file's text cannot be read or is empty."""


class AnthropicAPIError(DocumentPipelineError):
    """Raised when the Anthropic API returns an error response."""


class AnthropicTimeoutError(DocumentPipelineError):
    """Raised when a request to the Anthropic API times out."""


class MalformedAgentOutputError(DocumentPipelineError):
    """Raised when an agent's response cannot be parsed as a JSON object."""


class ValidationError(DocumentPipelineError):
    """Base class for schema-validation failures of an agent's JSON output."""


class ExtractionValidationError(ValidationError):
    """Raised when the Extraction Agent's JSON fails schema validation."""


class AnalysisValidationError(ValidationError):
    """Raised when the Analysis Agent's JSON fails schema validation."""


@dataclass(frozen=True)
class ExtractedSection:
    """A single section of a structured document.

    Attributes:
        heading: The section's heading text.
        content: The section's body text, preserved verbatim.
    """

    heading: str
    content: str

    def to_dict(self) -> dict[str, Any]:
        """Convert this section to the plain dict shape used in JSON.

        Returns:
            A dict with ``heading`` and ``content`` keys.
        """
        return {"heading": self.heading, "content": self.content}


@dataclass(frozen=True)
class ExtractedDocument:
    """The structured output of the Extraction Agent.

    Attributes:
        title: The document's title.
        metadata: Free-form metadata extracted from the document (may be empty).
        sections: The document's sections, in original order.
    """

    title: str
    metadata: dict[str, Any]
    sections: tuple[ExtractedSection, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert this document to the plain dict shape used in JSON.

        Returns:
            A dict with ``title``, ``metadata``, and ``sections`` keys.
        """
        return {
            "title": self.title,
            "metadata": dict(self.metadata),
            "sections": [section.to_dict() for section in self.sections],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractedDocument:
        """Build an ExtractedDocument from an already-validated dict.

        Args:
            data: A dict that has already passed
                :func:`document_pipeline.validation.validate_extraction_output`.

        Returns:
            The equivalent ExtractedDocument.
        """
        sections = tuple(
            ExtractedSection(heading=section["heading"], content=section["content"])
            for section in data["sections"]
        )
        return cls(title=data["title"], metadata=dict(data["metadata"]), sections=sections)


@dataclass(frozen=True)
class Claim:
    """A factual claim identified by the Analysis Agent.

    Attributes:
        text: The claim's text.
        confidence: Confidence score in the inclusive range [0.0, 1.0].
    """

    text: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        """Convert this claim to the plain dict shape used in JSON.

        Returns:
            A dict with ``text`` and ``confidence`` keys.
        """
        return {"text": self.text, "confidence": self.confidence}


@dataclass(frozen=True)
class Entity:
    """A named entity identified by the Analysis Agent.

    Attributes:
        name: The entity's name.
        type: The entity's type (e.g. "Organization", "Person").
        confidence: Confidence score in the inclusive range [0.0, 1.0].
    """

    name: str
    type: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        """Convert this entity to the plain dict shape used in JSON.

        Returns:
            A dict with ``name``, ``type``, and ``confidence`` keys.
        """
        return {"name": self.name, "type": self.type, "confidence": self.confidence}


@dataclass(frozen=True)
class Topic:
    """A major topic identified by the Analysis Agent.

    Attributes:
        topic: The topic label.
        confidence: Confidence score in the inclusive range [0.0, 1.0].
    """

    topic: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        """Convert this topic to the plain dict shape used in JSON.

        Returns:
            A dict with ``topic`` and ``confidence`` keys.
        """
        return {"topic": self.topic, "confidence": self.confidence}


@dataclass(frozen=True)
class AnalysisResult:
    """The structured output of the Analysis Agent.

    Attributes:
        claims: Factual claims identified in the extracted document.
        entities: Named entities identified in the extracted document.
        topics: Major topics identified in the extracted document.
    """

    claims: tuple[Claim, ...]
    entities: tuple[Entity, ...]
    topics: tuple[Topic, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert this analysis result to the plain dict shape used in JSON.

        Returns:
            A dict with ``claims``, ``entities``, and ``topics`` keys.
        """
        return {
            "claims": [claim.to_dict() for claim in self.claims],
            "entities": [entity.to_dict() for entity in self.entities],
            "topics": [topic.to_dict() for topic in self.topics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisResult:
        """Build an AnalysisResult from an already-validated dict.

        Args:
            data: A dict that has already passed
                :func:`document_pipeline.validation.validate_analysis_output`.

        Returns:
            The equivalent AnalysisResult.
        """
        claims = tuple(
            Claim(text=claim["text"], confidence=float(claim["confidence"]))
            for claim in data["claims"]
        )
        entities = tuple(
            Entity(
                name=entity["name"],
                type=entity["type"],
                confidence=float(entity["confidence"]),
            )
            for entity in data["entities"]
        )
        topics = tuple(
            Topic(topic=topic["topic"], confidence=float(topic["confidence"]))
            for topic in data["topics"]
        )
        return cls(claims=claims, entities=entities, topics=topics)


@dataclass(frozen=True)
class SynthesisReport:
    """The final structured report produced by the Synthesis Agent.

    Attributes:
        executive_summary: A concise synthesis of the analysis data.
        main_claims: The most important claims from the analysis.
        key_entities: The most important entities from the analysis.
        major_topics: The most important topics from the analysis.
        overall_confidence: An aggregate confidence score in [0.0, 1.0].
    """

    executive_summary: str
    main_claims: tuple[Any, ...] = field(default_factory=tuple)
    key_entities: tuple[Any, ...] = field(default_factory=tuple)
    major_topics: tuple[Any, ...] = field(default_factory=tuple)
    overall_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert this report to the plain dict shape used in JSON.

        Returns:
            A dict with ``executive_summary``, ``main_claims``,
            ``key_entities``, ``major_topics``, and ``overall_confidence`` keys.
        """
        return {
            "executive_summary": self.executive_summary,
            "main_claims": list(self.main_claims),
            "key_entities": list(self.key_entities),
            "major_topics": list(self.major_topics),
            "overall_confidence": self.overall_confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SynthesisReport:
        """Build a SynthesisReport from an already-parsed dict.

        Args:
            data: The parsed JSON object returned by the Synthesis Agent.

        Returns:
            The equivalent SynthesisReport.
        """
        return cls(
            executive_summary=data["executive_summary"],
            main_claims=tuple(data.get("main_claims", ())),
            key_entities=tuple(data.get("key_entities", ())),
            major_topics=tuple(data.get("major_topics", ())),
            overall_confidence=float(data.get("overall_confidence", 0.0)),
        )
