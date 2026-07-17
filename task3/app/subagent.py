"""The fraud-analysis subagent: deeper reasoning on a specialist model.

This subagent is invoked by the main agent loop only under specific
trigger conditions. It never talks to the user directly — its output is
plain text handed back to the main agent, which folds it into its own
system prompt for the next Claude call.
"""

from __future__ import annotations

from typing import Any

from app import config
from app.anthropic_client import AnthropicAgentClient
from app.prompts import SUBAGENT_SYSTEM_PROMPT

_SUBAGENT_CONFIDENCE_TRIGGER = 0.7
_SUBAGENT_FLAG_COUNT_TRIGGER = 2


def should_invoke_subagent(
    flags: list[str],
    confidence: float,
    *,
    evidence_conflict: bool = False,
    active_fraud_suspected: bool = False,
) -> bool:
    """Decide whether the fraud-analysis subagent should be invoked.

    Args:
        flags: Red flags detected so far for the current message.
        confidence: The main agent's current confidence (0.0-1.0).
        evidence_conflict: Whether the conversation contains conflicting
            evidence about the message's legitimacy.
        active_fraud_suspected: Whether active, in-progress fraud is
            suspected (e.g. the user reports money already sent).

    Returns:
        True if any trigger condition is met.
    """
    return (
        len(flags) >= _SUBAGENT_FLAG_COUNT_TRIGGER
        or confidence < _SUBAGENT_CONFIDENCE_TRIGGER
        or evidence_conflict
        or active_fraud_suspected
    )


def run_fraud_analysis_subagent(
    conversation_context: str,
    fraud_tool_result: dict[str, Any],
    *,
    client: AnthropicAgentClient | None = None,
) -> str:
    """Run the specialist fraud-analysis subagent.

    Args:
        conversation_context: A summary or transcript excerpt describing
            the conversation so far.
        fraud_tool_result: The ``fraud_red_flag_check`` tool's output.
        client: An ``AnthropicAgentClient`` to use. Defaults to a fresh
            client configured for ``config.SUBAGENT_MODEL``
            (``claude-sonnet-4-5-20250929``).

    Returns:
        Plain-text deeper reasoning intended for the main agent only.

    Raises:
        app.models.SafeBankError: On API failure after retries, or if
            the subagent's response is malformed.
    """
    active_client = client or AnthropicAgentClient(model=config.SUBAGENT_MODEL)

    user_message = (
        "Conversation context:\n"
        f"{conversation_context}\n\n"
        "Fraud red-flag tool result:\n"
        f"{fraud_tool_result}\n\n"
        "Provide your deeper fraud-risk analysis for the main assistant."
    )

    return active_client.complete(
        SUBAGENT_SYSTEM_PROMPT,
        user_message,
        max_tokens=config.SUBAGENT_MAX_TOKENS,
    )
