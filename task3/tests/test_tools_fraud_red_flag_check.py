"""Tests for app.tools.fraud_red_flag_check and dispatch_tool_call."""

from __future__ import annotations

import pytest

from app.models import ToolExecutionError
from app.tools import dispatch_tool_call, fraud_red_flag_check
from tests.conftest import (
    FAKE_BVN_REQUEST_MESSAGE,
    FAKE_CUSTOMER_SUPPORT_MESSAGE,
    FAKE_OTP_SCAM_MESSAGE,
    LEGITIMATE_BANK_MESSAGE,
    PRIZE_SCAM_MESSAGE,
)


def test_legitimate_bank_message_is_low_risk():
    result = fraud_red_flag_check(LEGITIMATE_BANK_MESSAGE)
    assert result["risk_level"] == "low"
    assert result["flags"] == []


def test_fake_otp_scam_is_high_risk_with_expected_flags():
    result = fraud_red_flag_check(FAKE_OTP_SCAM_MESSAGE)
    assert result["risk_level"] == "high"
    assert "requests_otp" in result["flags"]
    assert "urgency_language" in result["flags"]
    assert "account_suspension_scam" in result["flags"]
    assert "suspicious_url" in result["flags"]


def test_fake_bvn_request_is_high_risk():
    result = fraud_red_flag_check(FAKE_BVN_REQUEST_MESSAGE)
    assert result["risk_level"] == "high"
    assert "requests_bvn" in result["flags"]


def test_fake_customer_support_message_flagged():
    result = fraud_red_flag_check(FAKE_CUSTOMER_SUPPORT_MESSAGE)
    assert "fake_customer_support" in result["flags"]
    assert "requests_pin" in result["flags"]
    assert result["risk_level"] == "high"


def test_prize_scam_flagged():
    result = fraud_red_flag_check(PRIZE_SCAM_MESSAGE)
    assert "prize_scam" in result["flags"]
    assert result["risk_level"] == "high"


def test_password_request_flagged_as_high_risk():
    result = fraud_red_flag_check("Please send your password now to verify your account.")
    assert "requests_password" in result["flags"]
    assert result["risk_level"] == "high"


def test_single_soft_flag_is_medium_risk():
    result = fraud_red_flag_check("Act now! This offer expires soon.")
    assert result["risk_level"] == "medium"


def test_two_soft_flags_escalate_to_high_risk():
    result = fraud_red_flag_check(
        "URGENT: act now, your account will be suspended if you do not respond immediately."
    )
    assert result["risk_level"] == "high"


def test_empty_message_raises_tool_execution_error():
    with pytest.raises(ToolExecutionError):
        fraud_red_flag_check("")


def test_non_string_message_raises_tool_execution_error():
    with pytest.raises(ToolExecutionError):
        fraud_red_flag_check(None)  # type: ignore[arg-type]


def test_dispatch_tool_call_executes_known_tool():
    result = dispatch_tool_call("fraud_red_flag_check", {"message": LEGITIMATE_BANK_MESSAGE})
    assert result["risk_level"] == "low"


def test_dispatch_tool_call_rejects_unknown_tool():
    with pytest.raises(ToolExecutionError, match="Unknown tool"):
        dispatch_tool_call("delete_account", {"message": "hi"})


def test_dispatch_tool_call_rejects_missing_message_field():
    with pytest.raises(ToolExecutionError):
        dispatch_tool_call("fraud_red_flag_check", {})


def test_dispatch_tool_call_rejects_non_dict_input():
    with pytest.raises(ToolExecutionError):
        dispatch_tool_call("fraud_red_flag_check", "not a dict")  # type: ignore[arg-type]
