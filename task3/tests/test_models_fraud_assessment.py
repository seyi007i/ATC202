"""Tests for Pydantic validation of app.models.FraudAssessment and friends."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import ChatRequest, FraudAssessment, FraudRedFlagResult


def test_valid_fraud_assessment():
    assessment = FraudAssessment(
        risk_level="high",
        confidence=0.95,
        flags=["requests_otp", "urgency_language"],
        recommended_actions=["Do not click links.", "Contact your bank."],
        should_escalate=True,
    )
    assert assessment.risk_level == "high"
    assert assessment.confidence == 0.95


@pytest.mark.parametrize("bad_risk_level", ["critical", "None", "HIGH", ""])
def test_invalid_risk_level_rejected(bad_risk_level):
    with pytest.raises(ValidationError):
        FraudAssessment(
            risk_level=bad_risk_level,
            confidence=0.5,
            flags=[],
            recommended_actions=["Be careful."],
            should_escalate=False,
        )


@pytest.mark.parametrize("bad_confidence", [-0.1, 1.1, 2.0, -5])
def test_out_of_range_confidence_rejected(bad_confidence):
    with pytest.raises(ValidationError):
        FraudAssessment(
            risk_level="low",
            confidence=bad_confidence,
            flags=[],
            recommended_actions=["Stay alert."],
            should_escalate=False,
        )


@pytest.mark.parametrize("boundary_confidence", [0.0, 1.0])
def test_boundary_confidence_accepted(boundary_confidence):
    assessment = FraudAssessment(
        risk_level="low",
        confidence=boundary_confidence,
        flags=[],
        recommended_actions=["Stay alert."],
        should_escalate=False,
    )
    assert assessment.confidence == boundary_confidence


def test_empty_recommended_actions_rejected():
    with pytest.raises(ValidationError, match="recommended_actions must not be empty"):
        FraudAssessment(
            risk_level="low",
            confidence=0.5,
            flags=[],
            recommended_actions=[],
            should_escalate=False,
        )


def test_non_bool_should_escalate_rejected():
    with pytest.raises(ValidationError):
        FraudAssessment(
            risk_level="low",
            confidence=0.5,
            flags=[],
            recommended_actions=["Stay alert."],
            should_escalate="yes please",
        )


def test_fraud_red_flag_result_requires_risk_level():
    with pytest.raises(ValidationError):
        FraudRedFlagResult(flags=[], recommendation="Be careful.")


def test_chat_request_rejects_blank_message():
    with pytest.raises(ValidationError):
        ChatRequest(session_id="abc", message="   ")


def test_chat_request_accepts_valid_payload():
    request = ChatRequest(session_id="abc", message="Is this a scam?")
    assert request.message == "Is this a scam?"
