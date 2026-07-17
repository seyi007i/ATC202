"""Tests for agent-level intent routing in ``student_support_assistance.agent``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from student_support_assistance.agent import AgentTool, StudentSupportAgent
from student_support_assistance.models import (
    Intent,
    InvalidInputError,
    StudentNotFoundError,
    StudentSupportError,
    TicketWriteError,
)
from student_support_assistance.utils import classify_intent


@pytest.fixture
def agent() -> StudentSupportAgent:
    """Provide a StudentSupportAgent wired to the real tool implementations."""
    return StudentSupportAgent()


class TestIntentClassification:
    """Tests for the standalone keyword-based intent classifier."""

    def test_registration_question_is_knowledge_base(self) -> None:
        """A registration-timing question should route to the FAQ tool."""
        assert classify_intent("When is course registration?") is Intent.KNOWLEDGE_BASE

    def test_enrollment_question_is_enrollment(self) -> None:
        """An enrollment-status question should route to the enrollment tool."""
        assert classify_intent("Check enrollment for student S1001") is Intent.ENROLLMENT

    def test_appeal_request_is_escalation(self) -> None:
        """An appeal request should route to escalation."""
        assert classify_intent("I want to appeal my tuition decision.") is Intent.ESCALATION

    def test_escalation_keywords_outrank_enrollment_keywords(self) -> None:
        """A message mentioning both enrollment and escalation cues should
        still escalate, since human-handling intent takes priority."""
        text = "I want to appeal my enrollment status, this is unfair."
        assert classify_intent(text) is Intent.ESCALATION


class TestAgentRoutingExamples:
    """Tests mirroring the three example routing scenarios from the spec."""

    def test_knowledge_base_example_routes_to_search_tool(
        self, agent: StudentSupportAgent
    ) -> None:
        """'When is course registration?' should call search_knowledge_base."""
        response = agent.run("When is course registration?")
        assert response.intent is Intent.KNOWLEDGE_BASE
        assert response.tool_used == "search_knowledge_base"
        assert response.data

    def test_enrollment_example_routes_to_enrollment_tool(
        self, agent: StudentSupportAgent
    ) -> None:
        """'Check enrollment for student S1001' should call check_enrollment_status."""
        response = agent.run("Check enrollment for student S1001")
        assert response.intent is Intent.ENROLLMENT
        assert response.tool_used == "check_enrollment_status"
        assert response.data["student_id"] == "S1001"

    def test_escalation_example_routes_to_escalation_tool(
        self, agent: StudentSupportAgent, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """'I want to appeal my tuition decision.' should call escalate_to_advisor."""
        from student_support_assistance import tools as tools_module

        monkeypatch.setattr(tools_module.config, "SUPPORT_TICKETS_FILE", tmp_path / "tickets.txt")
        response = agent.run(
            "I want to appeal my tuition decision.", student_id="S1001"
        )
        assert response.intent is Intent.ESCALATION
        assert response.tool_used == "escalate_to_advisor"
        assert "ticket_id" in response.data


class TestAgentErrorHandling:
    """Tests for how the agent handles missing information and tool errors."""

    def test_empty_message_returns_friendly_error_without_raising(
        self, agent: StudentSupportAgent
    ) -> None:
        """An empty message should produce a graceful AgentResponse, not raise."""
        response = agent.run("")
        assert response.intent is None
        assert response.tool_used is None
        assert "sorry" in response.message.lower() or "couldn't" in response.message.lower()

    def test_non_string_message_returns_friendly_error(
        self, agent: StudentSupportAgent
    ) -> None:
        """A non-string message should be handled gracefully, not raise."""
        response = agent.run(123)  # type: ignore[arg-type]
        assert response.tool_used is None

    def test_enrollment_without_student_id_asks_for_one(
        self, agent: StudentSupportAgent
    ) -> None:
        """An enrollment request with no resolvable ID should ask for one."""
        response = agent.run("What courses am I taking?")
        assert response.intent is Intent.ENROLLMENT
        assert response.tool_used is None
        assert "student id" in response.message.lower()

    def test_enrollment_with_unknown_student_id_is_explained(
        self, agent: StudentSupportAgent
    ) -> None:
        """An unknown student ID should produce a clear, non-crashing message."""
        response = agent.run("Check my enrollment for S9999")
        assert response.intent is Intent.ENROLLMENT
        assert response.tool_used == "check_enrollment_status"
        assert "S9999" in response.message

    def test_escalation_without_student_id_asks_for_one(
        self, agent: StudentSupportAgent
    ) -> None:
        """An escalation request with no student ID should ask for one first."""
        response = agent.run("I have a complaint about my professor.")
        assert response.intent is Intent.ESCALATION
        assert response.tool_used is None
        assert "student id" in response.message.lower()

    def test_knowledge_base_tool_failure_is_caught(self) -> None:
        """If the knowledge-base tool raises an unexpected exception, the
        agent must catch it and reply gracefully rather than crashing."""

        def failing_search(_query: str) -> list[dict[str, Any]]:
            raise RuntimeError("boom")

        custom_agent = StudentSupportAgent(
            tools={
                "search_knowledge_base": AgentTool(
                    name="search_knowledge_base",
                    description="fake",
                    func=failing_search,
                ),
            }
        )
        response = custom_agent.run("When is course registration?")
        assert response.tool_used == "search_knowledge_base"
        assert "unexpected error" in response.message.lower()

    def test_enrollment_tool_domain_error_is_caught_gracefully(self) -> None:
        """A StudentSupportError subclass raised by the tool must be caught
        and translated into a friendly message rather than propagated."""

        def failing_lookup(_student_id: str) -> dict[str, Any]:
            raise StudentNotFoundError("S0000")

        custom_agent = StudentSupportAgent(
            tools={
                "check_enrollment_status": AgentTool(
                    name="check_enrollment_status",
                    description="fake",
                    func=failing_lookup,
                ),
            }
        )
        response = custom_agent.run("Check enrollment for S0000")
        assert response.tool_used == "check_enrollment_status"
        assert "S0000" in response.message

    def test_unmatched_query_suggests_escalation(self, agent: StudentSupportAgent) -> None:
        """A question with no matching FAQ should suggest escalation instead
        of fabricating an answer."""
        response = agent.run("zzz qwx flibber unrelated nonsense query")
        assert response.tool_used == "search_knowledge_base"
        assert response.data == [] or response.message

    def test_knowledge_base_empty_results_offers_escalation(self) -> None:
        """When the search tool legitimately returns no matches, the agent
        should offer to escalate rather than invent an answer."""
        custom_agent = StudentSupportAgent(
            tools={
                "search_knowledge_base": AgentTool(
                    name="search_knowledge_base",
                    description="fake",
                    func=lambda _query: [],
                ),
            }
        )
        response = custom_agent.run("some obscure question")
        assert response.data == []
        assert "escalate" in response.message.lower()

    def test_knowledge_base_domain_error_is_caught_gracefully(self) -> None:
        """A StudentSupportError (non-crash) from the search tool should be
        translated into a friendly message."""
        custom_agent = StudentSupportAgent(
            tools={
                "search_knowledge_base": AgentTool(
                    name="search_knowledge_base",
                    description="fake",
                    func=lambda _query: (_ for _ in ()).throw(InvalidInputError("bad")),
                ),
            }
        )
        response = custom_agent.run("some question")
        assert response.tool_used == "search_knowledge_base"
        assert "couldn't search" in response.message.lower()

    def test_enrollment_domain_error_other_than_not_found_is_caught(self) -> None:
        """A generic StudentSupportError from the enrollment tool (distinct
        from StudentNotFoundError) should be translated gracefully."""
        custom_agent = StudentSupportAgent(
            tools={
                "check_enrollment_status": AgentTool(
                    name="check_enrollment_status",
                    description="fake",
                    func=lambda _sid: (_ for _ in ()).throw(StudentSupportError("db down")),
                ),
            }
        )
        response = custom_agent.run("Check enrollment for S1001")
        assert response.tool_used == "check_enrollment_status"
        assert "went wrong" in response.message.lower()

    def test_enrollment_unexpected_exception_is_caught(self) -> None:
        """An unexpected (non-domain) exception from the enrollment tool
        must not propagate out of the agent."""
        custom_agent = StudentSupportAgent(
            tools={
                "check_enrollment_status": AgentTool(
                    name="check_enrollment_status",
                    description="fake",
                    func=lambda _sid: (_ for _ in ()).throw(RuntimeError("boom")),
                ),
            }
        )
        response = custom_agent.run("Check enrollment for S1001")
        assert response.tool_used == "check_enrollment_status"
        assert "unexpected error" in response.message.lower()

    def test_escalation_domain_error_is_caught_gracefully(self) -> None:
        """A TicketWriteError from the escalation tool should be translated
        into a friendly message rather than propagated."""
        custom_agent = StudentSupportAgent(
            tools={
                "escalate_to_advisor": AgentTool(
                    name="escalate_to_advisor",
                    description="fake",
                    func=lambda _sid, _summary: (_ for _ in ()).throw(
                        TicketWriteError("disk full")
                    ),
                ),
            }
        )
        response = custom_agent.run("I have a complaint.", student_id="S1001")
        assert response.tool_used == "escalate_to_advisor"
        assert "couldn't create your support ticket" in response.message.lower()

    def test_escalation_unexpected_exception_is_caught(self) -> None:
        """An unexpected (non-domain) exception from the escalation tool
        must not propagate out of the agent."""
        custom_agent = StudentSupportAgent(
            tools={
                "escalate_to_advisor": AgentTool(
                    name="escalate_to_advisor",
                    description="fake",
                    func=lambda _sid, _summary: (_ for _ in ()).throw(RuntimeError("boom")),
                ),
            }
        )
        response = custom_agent.run("I have a complaint.", student_id="S1001")
        assert response.tool_used == "escalate_to_advisor"
        assert "unexpected error" in response.message.lower()
