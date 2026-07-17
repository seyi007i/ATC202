"""Data models and structured exceptions for the Student Support Assistant.

All cross-module data contracts live here as immutable dataclasses so that
tools, the agent, and tests share a single source of truth for shapes and
validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StudentSupportError(Exception):
    """Base class for all application-specific errors.

    Catching this (instead of bare ``Exception``) lets callers distinguish
    expected, user-facing failures (bad input, unknown student, etc.) from
    genuine bugs.
    """


class InvalidInputError(StudentSupportError):
    """Raised when a caller-supplied argument fails basic type/shape checks.

    Examples include a non-string ``query``, a ``None`` ``student_id``, or a
    query that is empty after stripping whitespace.
    """


class EmptyQueryError(InvalidInputError):
    """Raised when a search query is empty or contains only whitespace."""


class StudentNotFoundError(StudentSupportError):
    """Raised when a lookup is performed for an unknown student ID."""

    def __init__(self, student_id: str) -> None:
        """Initialize the error with the offending student ID.

        Args:
            student_id: The student ID that could not be found.
        """
        self.student_id = student_id
        super().__init__(f"No student record found for ID '{student_id}'.")


class TicketWriteError(StudentSupportError):
    """Raised when an escalation ticket cannot be persisted to disk."""


class KnowledgeBaseError(StudentSupportError):
    """Raised when the FAQ knowledge base cannot be searched."""


class Intent(str, Enum):
    """Enumerates the intents the agent can route a user message to."""

    KNOWLEDGE_BASE = "knowledge_base"
    ENROLLMENT = "enrollment"
    ESCALATION = "escalation"


@dataclass(frozen=True)
class FAQEntry:
    """A single question/answer pair in the knowledge base.

    Attributes:
        question: The canonical phrasing of the FAQ question.
        answer: The answer text shown to the student.
        tags: Optional extra keywords that improve search recall.
    """

    question: str
    answer: str
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FAQSearchResult:
    """A scored FAQ match returned by a knowledge-base search.

    Attributes:
        question: The matched FAQ question.
        answer: The matched FAQ answer.
        score: Relevance score in the inclusive range [0.0, 1.0].
    """

    question: str
    answer: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        """Convert this result to the plain dict shape the tool returns.

        Returns:
            A dict with ``question``, ``answer``, and ``score`` keys.
        """
        return {"question": self.question, "answer": self.answer, "score": self.score}


@dataclass(frozen=True)
class StudentRecord:
    """A student's enrollment record.

    Attributes:
        student_id: The student's unique identifier, e.g. "S1001".
        status: Human-readable enrollment status, e.g. "Enrolled".
        courses: Course names the student is currently taking.
    """

    student_id: str
    status: str
    courses: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert this record to the plain dict shape the tool returns.

        Returns:
            A dict with ``student_id``, ``status``, and ``courses`` keys.
        """
        return {
            "student_id": self.student_id,
            "status": self.status,
            "courses": list(self.courses),
        }


@dataclass(frozen=True)
class EscalationTicket:
    """A support ticket created for a request escalated to a human advisor.

    Attributes:
        ticket_id: Unique ticket identifier (a UUID4 string).
        student_id: The student the ticket was raised for.
        query_summary: A short description of the unresolved request.
        status: Lifecycle status of the ticket, e.g. "created".
    """

    ticket_id: str
    student_id: str
    query_summary: str
    status: str = "created"

    def to_dict(self) -> dict[str, Any]:
        """Convert this ticket to the plain dict shape the tool returns.

        Returns:
            A dict with ``ticket_id`` and ``status`` keys, matching the
            tool specification.
        """
        return {"ticket_id": self.ticket_id, "status": self.status}


@dataclass
class AgentResponse:
    """The result of a single agent turn.

    Attributes:
        intent: The intent the agent decided the message expressed, or
            ``None`` if the message could not be classified (e.g. it was
            invalid input rejected before routing).
        tool_used: Name of the tool function that was invoked, if any.
        message: A human-friendly reply suitable for display to the user.
        data: The raw structured payload returned by the invoked tool.
    """

    intent: Intent | None
    tool_used: str | None
    message: str
    data: Any = None
