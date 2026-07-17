"""Tests for app.agent_loop.AgentLoop: the 6-step agent loop."""

from __future__ import annotations

from app.agent_loop import FALLBACK_MAX_STEPS_MESSAGE, AgentLoop
from app.conversation import ConversationManager
from app.escalation import EscalationStore
from tests.conftest import FakeAgentClient, TextTurn, ToolUseTurn


def _make_loop(main_turns, *, subagent_responses=None, max_steps=6, escalation_path=None, tmp_path=None):
    main_client = FakeAgentClient(turns=list(main_turns))
    subagent_client = FakeAgentClient(complete_responses=list(subagent_responses or []))
    conversation_manager = ConversationManager(summarize_after_turns=10)
    store = EscalationStore(path=escalation_path or (tmp_path / "escalations.jsonl"))
    loop = AgentLoop(
        main_client=main_client,
        subagent_client=subagent_client,
        conversation_manager=conversation_manager,
        escalation_store=store,
        max_steps=max_steps,
    )
    return loop, main_client, subagent_client, conversation_manager


def test_answers_directly_when_no_tool_call_needed(tmp_path):
    loop, main_client, _, _ = _make_loop([TextTurn(text="You're safe, no action needed.")], tmp_path=tmp_path)
    response = loop.run_turn("s1", "How do I keep my account safe?")
    assert response.reply == "You're safe, no action needed."
    assert response.fraud_assessment is None
    assert response.escalation is None
    assert len(main_client.complete_with_tools_calls) == 1


def test_tool_call_then_high_risk_assessment_triggers_escalation(tmp_path):
    assessment_block = (
        "This looks like a scam. Please do not respond.\n"
        "```safebank-assessment\n"
        '{"risk_level": "high", "confidence": 0.95, "flags": ["requests_otp"], '
        '"recommended_actions": ["Contact your bank.", "Do not share your OTP."], '
        '"should_escalate": true}\n'
        "```"
    )
    turns = [
        ToolUseTurn(tool_calls=[{"id": "call_1", "name": "fraud_red_flag_check", "input": {"message": "share your otp now"}}]),
        TextTurn(text=assessment_block),
    ]
    loop, main_client, _, conversation_manager = _make_loop(turns, tmp_path=tmp_path)

    response = loop.run_turn("s1", "Is this a scam? They asked me to share my otp now")

    assert "safebank-assessment" not in response.reply
    assert response.fraud_assessment is not None
    assert response.fraud_assessment.risk_level == "high"
    assert response.escalation is not None
    assert response.escalation.ticket_id.startswith("ESC-")
    assert conversation_manager.get_or_create("s1").escalated is True
    assert response.suggested_actions == ["Contact your bank.", "Do not share your OTP."]


def test_max_steps_reached_returns_fallback_message(tmp_path):
    tool_turn = ToolUseTurn(tool_calls=[{"id": "call_1", "name": "fraud_red_flag_check", "input": {"message": "hi"}}])
    turns = [tool_turn, tool_turn, tool_turn]
    loop, main_client, _, _ = _make_loop(turns, max_steps=3, tmp_path=tmp_path)

    response = loop.run_turn("s1", "keeps calling the tool")

    assert response.reply == FALLBACK_MAX_STEPS_MESSAGE
    assert response.fraud_assessment is None
    assert len(main_client.complete_with_tools_calls) == 3


def test_subagent_notes_reach_system_prompt_but_never_the_user(tmp_path):
    turns = [
        ToolUseTurn(
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "fraud_red_flag_check",
                    "input": {"message": "URGENT: act now, your account will be suspended if you do not respond immediately."},
                }
            ]
        ),
        TextTurn(text="Everything looks fine to me. Thanks for checking!"),
    ]
    loop, main_client, subagent_client, _ = _make_loop(
        turns, subagent_responses=["SECRET_INTERNAL_NOTE_12345"], tmp_path=tmp_path
    )

    response = loop.run_turn("s1", "Is this suspicious?")

    assert "SECRET_INTERNAL_NOTE_12345" not in response.reply
    assert len(subagent_client.complete_calls) == 1
    second_call_system_prompt = main_client.complete_with_tools_calls[1][0]
    assert "SECRET_INTERNAL_NOTE_12345" in second_call_system_prompt
    assert "never quote" in second_call_system_prompt.lower()


def test_malformed_trailing_assessment_does_not_crash_the_turn(tmp_path):
    text = "Here's what I found.\n```safebank-assessment\n{not valid json at all\n```"
    loop, main_client, _, _ = _make_loop([TextTurn(text=text)], tmp_path=tmp_path)

    response = loop.run_turn("s1", "Check this message please")

    assert response.fraud_assessment is None
    assert "safebank-assessment" not in response.reply
    assert response.reply == "Here's what I found."


def test_tool_execution_error_does_not_crash_the_turn(tmp_path):
    turns = [
        ToolUseTurn(tool_calls=[{"id": "call_1", "name": "fraud_red_flag_check", "input": {}}]),
        TextTurn(text="I need a bit more detail to help you."),
    ]
    loop, main_client, _, _ = _make_loop(turns, tmp_path=tmp_path)

    response = loop.run_turn("s1", "Something happened but I'm not sure what")

    assert response.reply == "I need a bit more detail to help you."
    assert response.fraud_assessment is None


def test_low_risk_assessment_does_not_trigger_escalation(tmp_path):
    text = (
        "This looks safe.\n```safebank-assessment\n"
        '{"risk_level": "low", "confidence": 0.9, "flags": [], '
        '"recommended_actions": ["Stay alert."], "should_escalate": false}\n```'
    )
    loop, main_client, _, _ = _make_loop([TextTurn(text=text)], tmp_path=tmp_path)

    response = loop.run_turn("s1", "Is this a scam?")

    assert response.escalation is None
    assert response.fraud_assessment.should_escalate is False
