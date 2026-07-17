"""Tests for app.subagent (trigger logic and subagent invocation)."""

from __future__ import annotations

import pytest

from app import config
from app.subagent import run_fraud_analysis_subagent, should_invoke_subagent
from tests.conftest import FakeAgentClient


def test_no_trigger_when_low_flags_and_high_confidence():
    assert should_invoke_subagent(["urgency_language"], confidence=0.9) is False


def test_triggers_on_two_or_more_flags():
    assert should_invoke_subagent(["urgency_language", "suspicious_url"], confidence=0.9) is True


def test_triggers_on_low_confidence():
    assert should_invoke_subagent([], confidence=0.5) is True


def test_confidence_boundary_not_below_threshold():
    assert should_invoke_subagent([], confidence=0.7) is False


def test_triggers_on_evidence_conflict():
    assert should_invoke_subagent([], confidence=0.9, evidence_conflict=True) is True


def test_triggers_on_active_fraud_suspected():
    assert should_invoke_subagent([], confidence=0.9, active_fraud_suspected=True) is True


def test_run_fraud_analysis_subagent_returns_client_text_and_uses_given_client():
    fake_client = FakeAgentClient(complete_responses=["Deeper reasoning goes here."])
    result = run_fraud_analysis_subagent(
        "conversation context", {"risk_level": "high", "flags": ["requests_otp"]}, client=fake_client
    )
    assert result == "Deeper reasoning goes here."
    assert len(fake_client.complete_calls) == 1
    system_prompt, user_message, max_tokens = fake_client.complete_calls[0]
    assert "internal" in system_prompt.lower() or "subagent" in system_prompt.lower()
    assert "requests_otp" in user_message
    assert max_tokens == config.SUBAGENT_MAX_TOKENS
