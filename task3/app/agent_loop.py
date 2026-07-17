"""The SafeBank Companion agent loop.

One call to ``AgentLoop.run_turn`` processes one user message through up
to ``max_steps`` calls to the main Claude model. Each step is either a
tool call (which loops again with the tool result in context) or a
plain-text reply (which ends the loop). The loop stops when:

- The model produces a plain-text reply ("answered").
- A high-risk assessment triggers escalation ("escalation completed").
- ``max_steps`` calls have all been tool calls ("max steps reached").
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app import config
from app.anthropic_client import AnthropicAgentClient
from app.conversation import ConversationManager
from app.escalation import EscalationStore
from app.json_utils import extract_json_object
from app.models import (
    ChatResponse,
    FraudAssessment,
    FraudRedFlagResult,
    MalformedAgentOutputError,
    ToolExecutionError,
)
from app.prompts import ASSESSMENT_FENCE_TAG, SYSTEM_PROMPT, compose_system_prompt
from app.subagent import run_fraud_analysis_subagent, should_invoke_subagent
from app.tools import FRAUD_RED_FLAG_TOOL_SCHEMA, dispatch_tool_call

FALLBACK_MAX_STEPS_MESSAGE = (
    "I wasn't able to finish analyzing this within the allotted steps. "
    "Please try rephrasing your question, or contact your bank's official "
    "customer support channel if this is urgent."
)

_ASSESSMENT_BLOCK_PATTERN = re.compile(
    r"```" + re.escape(ASSESSMENT_FENCE_TAG) + r"\s*\n.*?```", re.DOTALL
)


def _estimate_confidence(tool_result: dict[str, Any]) -> float:
    """Derive a rough confidence estimate from a fraud tool result.

    This is an internal heuristic used only to decide whether the
    fraud-analysis subagent should be invoked; it is never shown to the
    user or validated as part of a ``FraudAssessment``.
    """
    risk_level = tool_result.get("risk_level")
    flag_count = len(tool_result.get("flags", []))
    if risk_level == "high" and flag_count >= 2:
        return 0.9
    if risk_level == "high":
        return 0.75
    if risk_level == "low":
        return 0.9
    return 0.5


def _extract_trailing_assessment(text: str) -> tuple[str, FraudAssessment | None]:
    """Strip and validate a trailing fenced FraudAssessment block, if present.

    Args:
        text: The assistant's raw reply text.

    Returns:
        A tuple of (display_text with the block removed, the validated
        FraudAssessment, or None if absent or invalid).
    """
    match = _ASSESSMENT_BLOCK_PATTERN.search(text)
    if not match:
        return text.strip(), None

    display_text = (text[: match.start()] + text[match.end() :]).strip()
    try:
        payload = extract_json_object(match.group(0), fence_tag=ASSESSMENT_FENCE_TAG)
        assessment = FraudAssessment.model_validate(payload)
    except (MalformedAgentOutputError, ValidationError):
        return display_text, None
    return display_text, assessment


class AgentLoop:
    """Orchestrates one chat turn: tool use, validation, and escalation."""

    def __init__(
        self,
        *,
        main_client: AnthropicAgentClient,
        conversation_manager: ConversationManager,
        escalation_store: EscalationStore,
        subagent_client: AnthropicAgentClient | None = None,
        max_steps: int = config.MAX_AGENT_STEPS,
    ) -> None:
        """Build an agent loop.

        Args:
            main_client: The client used for the main conversational model.
            conversation_manager: Tracks per-session history and summaries.
            escalation_store: Persists simulated escalation tickets.
            subagent_client: Client for the fraud-analysis subagent.
                Defaults to a fresh client on ``config.SUBAGENT_MODEL``.
            max_steps: Maximum main-model calls per user turn.
        """
        self._main_client = main_client
        self._conversations = conversation_manager
        self._escalations = escalation_store
        self._subagent_client = subagent_client
        self._max_steps = max_steps

    def run_turn(self, session_id: str, user_message: str) -> ChatResponse:
        """Process one user message and return the assistant's response.

        Args:
            session_id: The chat session id.
            user_message: The raw user message text.

        Returns:
            A validated :class:`app.models.ChatResponse`.

        Raises:
            app.models.InvalidInputError: If ``user_message`` is blank.
            app.models.SafeBankError: On unrecoverable API failure.
        """
        self._conversations.maybe_summarize(session_id)
        self._conversations.add_user_message(session_id, user_message)
        state = self._conversations.get_or_create(session_id)

        latest_assessment: FraudAssessment | None = None
        subagent_notes: str | None = None
        display_text = FALLBACK_MAX_STEPS_MESSAGE

        for _ in range(self._max_steps):
            system_prompt = compose_system_prompt(
                SYSTEM_PROMPT, summary=state.summary, subagent_notes=subagent_notes
            )
            messages = self._conversations.build_claude_messages(session_id)
            turn = self._main_client.complete_with_tools(
                system_prompt,
                messages,
                tools=[FRAUD_RED_FLAG_TOOL_SCHEMA],
                max_tokens=config.MAIN_MAX_TOKENS,
            )

            if turn.tool_calls:
                self._conversations.append_raw_assistant_turn(session_id, turn.raw_content)
                tool_result_blocks: list[dict[str, Any]] = []
                last_heuristic_result: dict[str, Any] | None = None

                for call in turn.tool_calls:
                    try:
                        result = dispatch_tool_call(call.name, call.input)
                        FraudRedFlagResult.model_validate(result)
                    except (ToolExecutionError, ValidationError) as exc:
                        result = {"error": str(exc)}
                    else:
                        last_heuristic_result = result
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call.id,
                            "content": json.dumps(result),
                        }
                    )

                self._conversations.append_raw_user_turn(session_id, tool_result_blocks)

                if last_heuristic_result is not None:
                    flags = last_heuristic_result.get("flags", [])
                    confidence_estimate = _estimate_confidence(last_heuristic_result)
                    if should_invoke_subagent(flags, confidence_estimate):
                        subagent_notes = run_fraud_analysis_subagent(
                            self._conversations.context_snapshot(session_id),
                            last_heuristic_result,
                            client=self._subagent_client,
                        )
                continue

            display_text, latest_assessment = _extract_trailing_assessment(turn.text or "")
            break
        else:
            display_text = FALLBACK_MAX_STEPS_MESSAGE

        escalation = None
        if latest_assessment is not None and latest_assessment.should_escalate and not state.escalated:
            escalation = self._escalations.create_escalation(session_id, latest_assessment, display_text)
            self._conversations.mark_escalated(session_id, escalation.ticket_id)

        self._conversations.add_assistant_message(session_id, display_text)
        if latest_assessment is not None:
            self._conversations.record_fraud_assessment(session_id, latest_assessment)

        return ChatResponse(
            reply=display_text,
            fraud_assessment=latest_assessment,
            escalation=escalation,
            suggested_actions=latest_assessment.recommended_actions if latest_assessment else [],
        )
