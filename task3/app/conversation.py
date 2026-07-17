"""Multi-turn conversation state, summarization, and PII redaction.

Conversation history is tracked in whole "exchanges" (one user message
through to the final assistant reply, including any tool-use/tool-result
sub-turns in between) rather than as a flat message list. Summarizing
and trimming only ever happens on whole, already-completed exchanges, so
the remaining Anthropic message transcript always preserves valid
user/assistant role alternation and intact tool_use/tool_result pairs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app import config
from app.anthropic_client import AnthropicAgentClient
from app.models import FraudAssessment, InvalidInputError, SafeBankError
from app.redaction import redact_sensitive

Role = Literal["user", "assistant"]

_SUMMARIZER_SYSTEM_PROMPT = (
    "Summarize this conversation about mobile-money fraud concisely, in "
    "under 150 words. Preserve key facts: suspicious messages discussed, "
    "risk assessments and recommendations already given, and any "
    "escalation status. Do not include any passwords, PINs, OTPs, BVNs, "
    "or full account numbers, even if present in the transcript."
)

_FALLBACK_SUMMARY_CHAR_LIMIT = 1000


@dataclass(frozen=True)
class ChatTurn:
    """One message entry in the Anthropic Messages API format."""

    role: Role
    content: list[dict[str, Any]]


@dataclass
class ConversationState:
    """All state tracked for a single chat session."""

    session_id: str
    exchanges: list[list[ChatTurn]] = field(default_factory=list)
    pending: list[ChatTurn] = field(default_factory=list)
    summary: str | None = None
    fraud_history: list[FraudAssessment] = field(default_factory=list)
    escalated: bool = False
    last_escalation_ticket_id: str | None = None


class ConversationManager:
    """Tracks per-session conversation state across chat turns."""

    def __init__(
        self,
        *,
        summarize_after_turns: int = config.SUMMARIZE_AFTER_TURNS,
        summarizer_client: AnthropicAgentClient | None = None,
    ) -> None:
        """Build a conversation manager.

        Args:
            summarize_after_turns: Number of completed exchanges to keep
                in full before older ones are summarized away.
            summarizer_client: Client used to generate summaries. If
                None, a crude character-truncation fallback is used
                instead of a Claude call.
        """
        self._states: dict[str, ConversationState] = {}
        self._summarize_after_turns = summarize_after_turns
        self._summarizer_client = summarizer_client

    def get_or_create(self, session_id: str) -> ConversationState:
        """Return the session's state, creating it if needed."""
        if session_id not in self._states:
            self._states[session_id] = ConversationState(session_id=session_id)
        return self._states[session_id]

    def add_user_message(self, session_id: str, raw_text: str) -> str:
        """Start a new pending exchange with a redacted user message.

        Args:
            session_id: The chat session id.
            raw_text: The raw text the user submitted.

        Returns:
            The redacted text that was stored and will be sent to Claude.

        Raises:
            InvalidInputError: If ``raw_text`` is blank.
        """
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise InvalidInputError("message must not be empty")

        redacted = redact_sensitive(raw_text)
        state = self.get_or_create(session_id)
        state.pending = [ChatTurn(role="user", content=[{"type": "text", "text": redacted}])]
        return redacted

    def append_raw_assistant_turn(self, session_id: str, content_blocks: list[dict[str, Any]]) -> None:
        """Append an assistant turn (e.g. containing tool_use) mid-exchange."""
        state = self.get_or_create(session_id)
        state.pending.append(ChatTurn(role="assistant", content=content_blocks))

    def append_raw_user_turn(self, session_id: str, content_blocks: list[dict[str, Any]]) -> None:
        """Append a user-role turn (e.g. containing tool_result) mid-exchange."""
        state = self.get_or_create(session_id)
        state.pending.append(ChatTurn(role="user", content=content_blocks))

    def add_assistant_message(self, session_id: str, text: str) -> None:
        """Append the final assistant reply and close out the exchange."""
        state = self.get_or_create(session_id)
        state.pending.append(ChatTurn(role="assistant", content=[{"type": "text", "text": text}]))
        state.exchanges.append(state.pending)
        state.pending = []

    def build_claude_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Build the full Anthropic ``messages`` list for this session."""
        state = self.get_or_create(session_id)
        turns = [turn for exchange in state.exchanges for turn in exchange] + state.pending
        return [{"role": turn.role, "content": turn.content} for turn in turns]

    def maybe_summarize(self, session_id: str) -> None:
        """Summarize the oldest exchanges once the session exceeds the turn cap.

        Only whole, completed exchanges are summarized and trimmed —
        never a partial (pending) exchange — so message role alternation
        and tool_use/tool_result pairing always stay intact.
        """
        state = self.get_or_create(session_id)
        if len(state.exchanges) <= self._summarize_after_turns:
            return

        excess = len(state.exchanges) - self._summarize_after_turns
        old_exchanges = state.exchanges[:excess]
        state.exchanges = state.exchanges[excess:]

        transcript = self._render_transcript(old_exchanges)
        summary_text = redact_sensitive(self._summarize(transcript))
        state.summary = f"{state.summary}\n{summary_text}" if state.summary else summary_text

    def record_fraud_assessment(self, session_id: str, assessment: FraudAssessment) -> None:
        """Record a validated fraud assessment in the session's history."""
        state = self.get_or_create(session_id)
        state.fraud_history.append(assessment)

    def mark_escalated(self, session_id: str, ticket_id: str) -> None:
        """Mark the session as having an active escalation."""
        state = self.get_or_create(session_id)
        state.escalated = True
        state.last_escalation_ticket_id = ticket_id

    def context_snapshot(self, session_id: str) -> str:
        """Return a human-readable conversation snapshot for internal use.

        Intended for the fraud-analysis subagent, which needs enough
        context to reason about the case without being handed the raw
        Anthropic message structures.
        """
        state = self.get_or_create(session_id)
        parts: list[str] = []
        if state.summary:
            parts.append(state.summary)
        recent = self._render_transcript(state.exchanges[-3:])
        if recent:
            parts.append(recent)
        pending_text = self._render_transcript([state.pending]) if state.pending else ""
        if pending_text:
            parts.append(pending_text)
        return "\n".join(parts) if parts else "(no prior context)"

    @staticmethod
    def _render_transcript(exchanges: list[list[ChatTurn]]) -> str:
        lines: list[str] = []
        for exchange in exchanges:
            for turn in exchange:
                texts = [block["text"] for block in turn.content if block.get("type") == "text"]
                if texts:
                    lines.append(f"{turn.role}: {' '.join(texts)}")
        return "\n".join(lines)

    def _summarize(self, transcript: str) -> str:
        if self._summarizer_client is None:
            return transcript[:_FALLBACK_SUMMARY_CHAR_LIMIT]
        try:
            return self._summarizer_client.complete(
                _SUMMARIZER_SYSTEM_PROMPT,
                transcript,
                max_tokens=config.SUMMARY_MAX_TOKENS,
            )
        except SafeBankError:
            return transcript[:_FALLBACK_SUMMARY_CHAR_LIMIT]
