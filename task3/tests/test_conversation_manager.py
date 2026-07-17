"""Tests for app.conversation.ConversationManager."""

from __future__ import annotations

from app.conversation import ConversationManager
from app.models import FraudAssessment
from tests.conftest import FakeAgentClient


def test_add_user_message_redacts_before_storing():
    manager = ConversationManager(summarize_after_turns=10)
    redacted = manager.add_user_message("s1", "My OTP is 123456")
    assert "123456" not in redacted
    messages = manager.build_claude_messages("s1")
    assert "123456" not in messages[0]["content"][0]["text"]


def test_full_exchange_round_trip_and_message_alternation():
    manager = ConversationManager(summarize_after_turns=10)
    manager.add_user_message("s1", "Is this a scam?")
    manager.append_raw_assistant_turn(
        "s1", [{"type": "tool_use", "id": "call_1", "name": "fraud_red_flag_check", "input": {"message": "x"}}]
    )
    manager.append_raw_user_turn(
        "s1", [{"type": "tool_result", "tool_use_id": "call_1", "content": "{}"}]
    )
    manager.add_assistant_message("s1", "Here is my answer.")

    messages = manager.build_claude_messages("s1")
    roles = [m["role"] for m in messages]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_maybe_summarize_triggers_after_turn_cap_with_fallback_truncation():
    manager = ConversationManager(summarize_after_turns=2, summarizer_client=None)
    for i in range(4):
        manager.add_user_message("s1", f"message {i}")
        manager.add_assistant_message("s1", f"reply {i}")

    manager.maybe_summarize("s1")
    state = manager.get_or_create("s1")
    assert len(state.exchanges) == 2
    assert state.summary is not None


def test_maybe_summarize_uses_summarizer_client_when_provided():
    fake_client = FakeAgentClient(complete_responses=["Condensed summary."])
    manager = ConversationManager(summarize_after_turns=1, summarizer_client=fake_client)
    manager.add_user_message("s1", "first message")
    manager.add_assistant_message("s1", "first reply")
    manager.add_user_message("s1", "second message")
    manager.add_assistant_message("s1", "second reply")

    manager.maybe_summarize("s1")
    state = manager.get_or_create("s1")
    assert state.summary == "Condensed summary."
    assert len(fake_client.complete_calls) == 1


def test_maybe_summarize_no_op_when_under_cap():
    manager = ConversationManager(summarize_after_turns=10)
    manager.add_user_message("s1", "hello")
    manager.add_assistant_message("s1", "hi there")
    manager.maybe_summarize("s1")
    state = manager.get_or_create("s1")
    assert state.summary is None
    assert len(state.exchanges) == 1


def test_record_fraud_assessment_and_mark_escalated():
    manager = ConversationManager(summarize_after_turns=10)
    assessment = FraudAssessment(
        risk_level="high",
        confidence=0.9,
        flags=["requests_otp"],
        recommended_actions=["Contact your bank."],
        should_escalate=True,
    )
    manager.record_fraud_assessment("s1", assessment)
    manager.mark_escalated("s1", "ESC-ABCD1234")

    state = manager.get_or_create("s1")
    assert state.fraud_history == [assessment]
    assert state.escalated is True
    assert state.last_escalation_ticket_id == "ESC-ABCD1234"


def test_sessions_are_isolated():
    manager = ConversationManager(summarize_after_turns=10)
    manager.add_user_message("s1", "hello from s1")
    manager.add_assistant_message("s1", "reply to s1")

    messages_s2 = manager.build_claude_messages("s2")
    assert messages_s2 == []


def test_context_snapshot_includes_summary_and_recent_exchanges():
    manager = ConversationManager(summarize_after_turns=10)
    manager.add_user_message("s1", "hello")
    manager.add_assistant_message("s1", "hi there")
    snapshot = manager.context_snapshot("s1")
    assert "hello" in snapshot
    assert "hi there" in snapshot
