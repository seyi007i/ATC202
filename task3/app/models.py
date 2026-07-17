"""Pydantic schemas and the SafeBank Companion exception hierarchy.

All structured data exchanged between Claude, the agent loop, and the
FastAPI layer is validated through the models defined here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

RiskLevel = Literal["low", "medium", "high"]


# --------------------------------------------------------------------------
# Exception hierarchy
# --------------------------------------------------------------------------


class SafeBankError(Exception):
    """Base class for all SafeBank Companion domain errors."""


class MissingAPIKeyError(SafeBankError):
    """Raised at startup when ANTHROPIC_API_KEY is not configured."""


class AnthropicTimeoutError(SafeBankError):
    """Raised when a request to the Anthropic API times out. Retryable."""


class AnthropicConnectionError(SafeBankError):
    """Raised on a network failure while calling the Anthropic API. Retryable."""


class AnthropicTemporaryError(SafeBankError):
    """Raised on a rate limit or server error (429/5xx). Retryable."""


class AnthropicAPIError(SafeBankError):
    """Raised on a non-retryable Anthropic API error (e.g. 4xx auth failure)."""


class MalformedAgentOutputError(SafeBankError):
    """Raised when Claude's response cannot be parsed as expected."""


class FraudAssessmentValidationError(SafeBankError):
    """Raised when a candidate FraudAssessment payload fails validation."""


class ToolExecutionError(SafeBankError):
    """Raised when a tool call fails or references an unknown tool."""


class InvalidInputError(SafeBankError):
    """Raised when user-supplied input fails basic validation."""


class EscalationWriteError(SafeBankError):
    """Raised when a simulated escalation record cannot be persisted."""


# --------------------------------------------------------------------------
# Tool I/O
# --------------------------------------------------------------------------


class FraudRedFlagResult(BaseModel):
    """Validated output of the ``fraud_red_flag_check`` tool."""

    risk_level: RiskLevel
    flags: list[str] = Field(default_factory=list)
    recommendation: str


# --------------------------------------------------------------------------
# Structured assessment produced by the main agent
# --------------------------------------------------------------------------


class FraudAssessment(BaseModel):
    """A fully validated fraud risk assessment for one conversation turn."""

    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    flags: list[str] = Field(default_factory=list)
    recommended_actions: list[str]
    should_escalate: bool

    @field_validator("recommended_actions")
    @classmethod
    def _recommended_actions_not_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("recommended_actions must not be empty")
        return value


# --------------------------------------------------------------------------
# Escalation
# --------------------------------------------------------------------------


class EscalationRecord(BaseModel):
    """A simulated escalation ticket for a high-risk case."""

    ticket_id: str
    session_id: str
    risk_level: RiskLevel
    summary: str
    created_at: datetime


# --------------------------------------------------------------------------
# API request/response contracts
# --------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Incoming payload for ``POST /api/chat``."""

    session_id: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    """Outgoing payload for ``POST /api/chat``."""

    reply: str
    fraud_assessment: FraudAssessment | None = None
    escalation: EscalationRecord | None = None
    suggested_actions: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """A friendly, user-facing error payload."""

    detail: str


# --------------------------------------------------------------------------
# Internal agent-loop data shapes
# --------------------------------------------------------------------------


class ToolCall(BaseModel):
    """A single tool invocation requested by Claude."""

    id: str
    name: str
    input: dict[str, Any]


class AgentTurnResult(BaseModel):
    """Normalized result of one call to the main Claude model."""

    text: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    stop_reason: str
    raw_content: list[dict[str, Any]] = Field(default_factory=list)
