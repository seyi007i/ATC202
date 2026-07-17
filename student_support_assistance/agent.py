"""Agent SDK core: tool registry, intent routing, and the public agent.

This module implements a small Agent/Tool/Runner pattern in the spirit of
the OpenAI Agents SDK, but fully local and deterministic: an
:class:`AgentTool` wraps a callable, :class:`StudentSupportAgent` holds a
registry of tools plus system instructions, and :meth:`StudentSupportAgent.run`
plays the role of a Runner — classifying the user's intent and invoking the
matching tool. No network or API key is required, which keeps the agent
fast and fully testable offline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from student_support_assistance.models import (
    AgentResponse,
    Intent,
    InvalidInputError,
    StudentNotFoundError,
    StudentSupportError,
)
from student_support_assistance.prompts import SYSTEM_PROMPT
from student_support_assistance.tools import (
    check_enrollment_status,
    escalate_to_advisor,
    search_knowledge_base,
)
from student_support_assistance.utils import (
    classify_intent,
    extract_student_id,
    require_non_empty_string,
    setup_logging,
)

logger = setup_logging()


@dataclass(frozen=True)
class AgentTool:
    """A named, callable capability the agent can invoke.

    Attributes:
        name: Unique tool name, used as the registry key.
        description: Human-readable summary of when to use the tool.
        func: The underlying callable that performs the tool's action.
    """

    name: str
    description: str
    func: Callable[..., Any]


def _default_tools() -> dict[str, AgentTool]:
    """Build the default tool registry backed by the real implementations.

    Returns:
        A dict mapping tool name to :class:`AgentTool`.
    """
    tools = (
        AgentTool(
            name="search_knowledge_base",
            description="Answer general, policy, tuition, deadline, "
            "registration, campus, admissions, payment, and graduation "
            "questions from the FAQ knowledge base.",
            func=search_knowledge_base,
        ),
        AgentTool(
            name="check_enrollment_status",
            description="Look up a student's enrollment status and "
            "current courses given a valid student ID.",
            func=check_enrollment_status,
        ),
        AgentTool(
            name="escalate_to_advisor",
            description="Open a support ticket for complaints, appeals, "
            "financial aid disputes, special requests, or explicit "
            "requests for a human advisor.",
            func=escalate_to_advisor,
        ),
    )
    return {tool.name: tool for tool in tools}


class StudentSupportAgent:
    """An agent that routes student messages to the right support tool.

    Attributes:
        instructions: The system prompt guiding the agent's behavior.
        tools: Registry of available :class:`AgentTool` instances, keyed
            by name. Overridable for testing (dependency injection).
    """

    def __init__(
        self,
        instructions: str = SYSTEM_PROMPT,
        tools: dict[str, AgentTool] | None = None,
    ) -> None:
        """Initialize the agent with instructions and a tool registry.

        Args:
            instructions: The system prompt guiding the agent's behavior.
            tools: Optional custom tool registry. Defaults to the real
                knowledge-base, enrollment, and escalation tools; tests
                may inject fakes/mocks here instead.
        """
        self.instructions = instructions
        self.tools = tools if tools is not None else _default_tools()

    def run(self, message: str, student_id: str | None = None) -> AgentResponse:
        """Process one user message and return the agent's response.

        Classifies the message's intent, resolves a student ID from either
        the explicit parameter or the message text, invokes the matching
        tool, and translates any tool error into a polite, human-readable
        explanation rather than raising it to the caller.

        Args:
            message: The student's free-text message.
            student_id: An explicitly known student ID, if any. Takes
                precedence over any ID mentioned in ``message``.

        Returns:
            An :class:`~student_support_assistance.models.AgentResponse`
            describing which intent/tool was used and a friendly reply.
        """
        try:
            clean_message = require_non_empty_string(message, "message")
        except InvalidInputError as exc:
            logger.warning("Rejected invalid message: %s", exc)
            return AgentResponse(
                intent=None,
                tool_used=None,
                message=f"I'm sorry, I couldn't process that: {exc}",
            )

        intent = classify_intent(clean_message)
        resolved_student_id = student_id or extract_student_id(clean_message)
        logger.info("Routed message to intent=%s", intent.value)

        if intent is Intent.ESCALATION:
            return self._handle_escalation(clean_message, resolved_student_id)
        if intent is Intent.ENROLLMENT:
            return self._handle_enrollment(resolved_student_id)
        return self._handle_knowledge_base(clean_message)

    def _handle_escalation(
        self, message: str, student_id: str | None
    ) -> AgentResponse:
        """Route a message classified as needing human escalation.

        Args:
            message: The original user message, used as the ticket summary.
            student_id: The resolved student ID, if one is known.

        Returns:
            An :class:`AgentResponse` describing the created ticket or the
            missing information needed to create one.
        """
        if not student_id:
            return AgentResponse(
                intent=Intent.ESCALATION,
                tool_used=None,
                message=(
                    "I'd like to connect you with a human advisor. Could "
                    "you first share your student ID so I can open a "
                    "ticket for you?"
                ),
            )
        try:
            ticket = self.tools["escalate_to_advisor"].func(student_id, message)
        except StudentSupportError as exc:
            return AgentResponse(
                intent=Intent.ESCALATION,
                tool_used="escalate_to_advisor",
                message=f"I'm sorry, I couldn't create your support ticket: {exc}",
            )
        except Exception as exc:  # noqa: BLE001 - tools are third-party-ish
            logger.exception("Unexpected error in escalate_to_advisor: %s", exc)
            return AgentResponse(
                intent=Intent.ESCALATION,
                tool_used="escalate_to_advisor",
                message=(
                    "I'm sorry, an unexpected error occurred while creating "
                    "your support ticket. Please try again shortly."
                ),
            )
        return AgentResponse(
            intent=Intent.ESCALATION,
            tool_used="escalate_to_advisor",
            message=(
                f"I've created support ticket {ticket['ticket_id']} and a "
                "human advisor will follow up with you soon."
            ),
            data=ticket,
        )

    def _handle_enrollment(self, student_id: str | None) -> AgentResponse:
        """Route a message classified as an enrollment-status request.

        Args:
            student_id: The resolved student ID, if one is known.

        Returns:
            An :class:`AgentResponse` describing the enrollment record or
            the error encountered while looking it up.
        """
        if not student_id:
            return AgentResponse(
                intent=Intent.ENROLLMENT,
                tool_used=None,
                message=(
                    "I can check your enrollment status, but I first need "
                    "a valid student ID (for example, S1001)."
                ),
            )
        try:
            record = self.tools["check_enrollment_status"].func(student_id)
        except StudentNotFoundError:
            return AgentResponse(
                intent=Intent.ENROLLMENT,
                tool_used="check_enrollment_status",
                message=(
                    f"I'm sorry, I couldn't find a student with ID "
                    f"'{student_id}'. Please double-check the ID and try "
                    "again."
                ),
            )
        except StudentSupportError as exc:
            return AgentResponse(
                intent=Intent.ENROLLMENT,
                tool_used="check_enrollment_status",
                message=(
                    "I'm sorry, something went wrong while checking your "
                    f"enrollment: {exc}"
                ),
            )
        except Exception as exc:  # noqa: BLE001 - tools are third-party-ish
            logger.exception("Unexpected error in check_enrollment_status: %s", exc)
            return AgentResponse(
                intent=Intent.ENROLLMENT,
                tool_used="check_enrollment_status",
                message=(
                    "I'm sorry, an unexpected error occurred while checking "
                    "your enrollment. Please try again shortly."
                ),
            )
        courses = ", ".join(record["courses"]) if record["courses"] else "none on record"
        return AgentResponse(
            intent=Intent.ENROLLMENT,
            tool_used="check_enrollment_status",
            message=(
                f"Your enrollment status is '{record['status']}'. "
                f"Courses: {courses}."
            ),
            data=record,
        )

    def _handle_knowledge_base(self, message: str) -> AgentResponse:
        """Route a message classified as a general knowledge-base question.

        Args:
            message: The original user message/question.

        Returns:
            An :class:`AgentResponse` with the best-matching FAQ answer, or
            a fallback message when no relevant FAQ exists.
        """
        try:
            results = self.tools["search_knowledge_base"].func(message)
        except StudentSupportError as exc:
            return AgentResponse(
                intent=Intent.KNOWLEDGE_BASE,
                tool_used="search_knowledge_base",
                message=f"I'm sorry, I couldn't search the knowledge base: {exc}",
            )
        except Exception as exc:  # noqa: BLE001 - tools are third-party-ish
            logger.exception("Unexpected error in search_knowledge_base: %s", exc)
            return AgentResponse(
                intent=Intent.KNOWLEDGE_BASE,
                tool_used="search_knowledge_base",
                message=(
                    "I'm sorry, an unexpected error occurred while searching "
                    "the knowledge base. Please try again shortly."
                ),
            )
        if not results:
            return AgentResponse(
                intent=Intent.KNOWLEDGE_BASE,
                tool_used="search_knowledge_base",
                message=(
                    "I couldn't find an FAQ that matches your question. "
                    "Would you like me to escalate this to a human advisor?"
                ),
                data=[],
            )
        return AgentResponse(
            intent=Intent.KNOWLEDGE_BASE,
            tool_used="search_knowledge_base",
            message=results[0]["answer"],
            data=results,
        )


def _run_demo_conversations() -> None:
    """Print a short transcript exercising all three tools, for `python -m`."""
    demo_agent = StudentSupportAgent()
    conversations = (
        ("When is course registration?", None),
        ("Check enrollment for student S1001", None),
        ("I want to appeal my tuition decision.", "S1001"),
    )
    for message, student_id in conversations:
        response = demo_agent.run(message, student_id=student_id)
        print(f"User: {message}")
        print(f"Agent [{response.tool_used or 'none'}]: {response.message}\n")


if __name__ == "__main__":
    _run_demo_conversations()
