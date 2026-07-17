"""Shared pytest fixtures and hand-rolled test fakes.

No mocking library is used anywhere in this test suite. Two tiers of
fakes are used:

- A low-level fake standing in for ``anthropic.Anthropic()`` itself
  (used only in ``test_anthropic_client.py`` to verify exception
  translation and response parsing).
- ``FakeAgentClient``, standing in for :class:`app.anthropic_client.AnthropicAgentClient`'s
  public surface (``.complete`` / ``.complete_with_tools``), used by
  every higher-level test (agent loop, conversation, subagent, routes)
  so nothing above the client wrapper ever touches the real SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.models import AgentTurnResult, ToolCall


@dataclass
class TextTurn:
    """Scripts a plain-text ``complete_with_tools`` response."""

    text: str
    stop_reason: str = "end_turn"


@dataclass
class ToolUseTurn:
    """Scripts a tool-use ``complete_with_tools`` response.

    Args:
        tool_calls: List of dicts with ``id``, ``name``, ``input`` keys.
    """

    tool_calls: list[dict[str, Any]]
    stop_reason: str = "tool_use"


class FakeAgentClient:
    """Stands in for ``AnthropicAgentClient``'s public interface."""

    def __init__(
        self,
        turns: list[Any] | None = None,
        complete_responses: list[str] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._turns = list(turns or [])
        self._complete_responses = list(complete_responses or [])
        self._error = error
        self.complete_calls: list[tuple[str, str, int]] = []
        self.complete_with_tools_calls: list[tuple[str, list, list, int]] = []

    def complete(self, system_prompt: str, user_message: str, *, max_tokens: int) -> str:
        self.complete_calls.append((system_prompt, user_message, max_tokens))
        if self._error is not None:
            raise self._error
        if self._complete_responses:
            return self._complete_responses.pop(0)
        return "Fake internal analysis response."

    def complete_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> AgentTurnResult:
        self.complete_with_tools_calls.append((system_prompt, messages, tools, max_tokens))
        if self._error is not None:
            raise self._error
        if not self._turns:
            raise AssertionError("FakeAgentClient ran out of scripted turns")

        turn = self._turns.pop(0)
        if isinstance(turn, ToolUseTurn):
            tool_calls = [ToolCall(**tc) for tc in turn.tool_calls]
            raw_content = [
                {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input}
                for tc in tool_calls
            ]
            return AgentTurnResult(
                text=None, tool_calls=tool_calls, stop_reason=turn.stop_reason, raw_content=raw_content
            )

        raw_content = [{"type": "text", "text": turn.text}]
        return AgentTurnResult(
            text=turn.text, tool_calls=[], stop_reason=turn.stop_reason, raw_content=raw_content
        )


@pytest.fixture
def fake_escalation_store(tmp_path):
    from app.escalation import EscalationStore

    return EscalationStore(path=tmp_path / "escalations.jsonl")


@pytest.fixture
def conversation_manager():
    from app.conversation import ConversationManager

    return ConversationManager(summarize_after_turns=10, summarizer_client=None)


# Sample messages used across scenario/tool tests.
LEGITIMATE_BANK_MESSAGE = (
    "Dear customer, your account was credited with NGN 15,000 on 12-Jul. "
    "Available balance is NGN 42,300. Thank you for banking with us."
)

FAKE_OTP_SCAM_MESSAGE = (
    "URGENT: Your account will be suspended within 24 hours. To reverse this, "
    "reply with the OTP sent to your phone immediately. http://bit.ly/verify-now"
)

FAKE_BVN_REQUEST_MESSAGE = (
    "This is your bank. We need to verify your BVN immediately, please send your "
    "BVN now or your account will be blocked."
)

FAKE_CUSTOMER_SUPPORT_MESSAGE = (
    "Hello, this is GTBank customer support. Please confirm your PIN with our "
    "support team so we can help you right away."
)

PRIZE_SCAM_MESSAGE = (
    "Congratulations you have won 500,000 naira in our promo! Claim your prize "
    "now by clicking www.claim-prize-now.com before it expires."
)

LOST_PHONE_MESSAGE = "I just lost my phone, what should I do to protect my bank account?"
