"""Tests for app.escalation.EscalationStore."""

from __future__ import annotations

import json

import pytest

from app.escalation import EscalationStore
from app.models import EscalationWriteError, FraudAssessment


def _sample_assessment() -> FraudAssessment:
    return FraudAssessment(
        risk_level="high",
        confidence=0.95,
        flags=["requests_otp"],
        recommended_actions=["Contact your bank."],
        should_escalate=True,
    )


def test_create_escalation_returns_record_with_ticket_id(tmp_path):
    store = EscalationStore(path=tmp_path / "escalations.jsonl")
    record = store.create_escalation("session-1", _sample_assessment(), "User received a fake OTP request.")
    assert record.ticket_id.startswith("ESC-")
    assert record.session_id == "session-1"
    assert record.risk_level == "high"


def test_create_escalation_persists_a_json_line(tmp_path):
    path = tmp_path / "escalations.jsonl"
    store = EscalationStore(path=path)
    record = store.create_escalation("session-1", _sample_assessment(), "Summary text.")

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    persisted = json.loads(lines[0])
    assert persisted["ticket_id"] == record.ticket_id


def test_create_escalation_redacts_summary_before_persisting(tmp_path):
    path = tmp_path / "escalations.jsonl"
    store = EscalationStore(path=path)
    store.create_escalation("session-1", _sample_assessment(), "My OTP is 123456, please help.")

    contents = path.read_text(encoding="utf-8")
    assert "123456" not in contents


def test_multiple_escalations_append_to_same_file(tmp_path):
    path = tmp_path / "escalations.jsonl"
    store = EscalationStore(path=path)
    store.create_escalation("session-1", _sample_assessment(), "First case.")
    store.create_escalation("session-2", _sample_assessment(), "Second case.")

    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_write_failure_raises_escalation_write_error(tmp_path):
    # Point the store at a path whose parent cannot be created (a file, not a directory).
    blocked_parent = tmp_path / "not_a_directory"
    blocked_parent.write_text("occupied", encoding="utf-8")
    store = EscalationStore(path=blocked_parent / "escalations.jsonl")

    with pytest.raises(EscalationWriteError):
        store.create_escalation("session-1", _sample_assessment(), "Summary.")
