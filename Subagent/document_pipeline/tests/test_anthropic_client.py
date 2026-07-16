"""Tests for document_pipeline.anthropic_client.

This is the one test module that stubs the underlying anthropic.Anthropic
SDK object directly (no real network calls) - every other test module fakes
AnthropicAgentClient's own .complete() interface instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import anthropic
import httpx
import pytest

from document_pipeline.anthropic_client import AnthropicAgentClient
from document_pipeline.models import AnthropicAPIError, AnthropicTimeoutError, MalformedAgentOutputError

_FAKE_REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


@dataclass
class _FakeContentBlock:
    """Stands in for an anthropic content block."""

    type: str
    text: str = ""


@dataclass
class _FakeResponse:
    """Stands in for an anthropic Message response."""

    content: list[_FakeContentBlock]
    stop_reason: str = "end_turn"


class _FakeMessages:
    """Stands in for anthropic.Anthropic().messages."""

    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.create_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> _FakeResponse:
        self.create_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return self._result


class _FakeAnthropicSDKClient:
    """Stands in for anthropic.Anthropic(), including with_options()."""

    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.messages = _FakeMessages(result, error)

    def with_options(self, *, timeout: float, max_retries: int) -> "_FakeAnthropicSDKClient":
        return self


def test_complete_returns_first_text_block() -> None:
    """complete() should return the first text content block's text."""
    response = _FakeResponse(content=[_FakeContentBlock(type="text", text='{"a": 1}')])
    fake_sdk_client = _FakeAnthropicSDKClient(result=response)
    client = AnthropicAgentClient(client=fake_sdk_client)

    result = client.complete("system", "user", max_tokens=100)

    assert result == '{"a": 1}'
    assert fake_sdk_client.messages.create_kwargs["system"] == "system"
    assert fake_sdk_client.messages.create_kwargs["messages"] == [{"role": "user", "content": "user"}]
    assert fake_sdk_client.messages.create_kwargs["max_tokens"] == 100


def test_skips_non_text_blocks() -> None:
    """complete() should skip non-text blocks and return the first text one."""
    response = _FakeResponse(
        content=[_FakeContentBlock(type="tool_use"), _FakeContentBlock(type="text", text="hello")]
    )
    fake_sdk_client = _FakeAnthropicSDKClient(result=response)
    client = AnthropicAgentClient(client=fake_sdk_client)

    assert client.complete("system", "user", max_tokens=100) == "hello"


def test_no_text_block_raises_malformed_agent_output_error() -> None:
    """A response with no text content block should raise."""
    response = _FakeResponse(content=[_FakeContentBlock(type="tool_use")])
    fake_sdk_client = _FakeAnthropicSDKClient(result=response)
    client = AnthropicAgentClient(client=fake_sdk_client)

    with pytest.raises(MalformedAgentOutputError):
        client.complete("system", "user", max_tokens=100)


def test_truncated_response_raises_malformed_agent_output_error() -> None:
    """A response with stop_reason='max_tokens' should raise, even if its
    partial text would otherwise look parseable."""
    response = _FakeResponse(
        content=[_FakeContentBlock(type="text", text='{"a": 1')],
        stop_reason="max_tokens",
    )
    fake_sdk_client = _FakeAnthropicSDKClient(result=response)
    client = AnthropicAgentClient(client=fake_sdk_client)

    with pytest.raises(MalformedAgentOutputError, match="truncated"):
        client.complete("system", "user", max_tokens=100)


def test_timeout_error_raises_anthropic_timeout_error() -> None:
    """anthropic.APITimeoutError should be translated to AnthropicTimeoutError."""
    fake_sdk_client = _FakeAnthropicSDKClient(error=anthropic.APITimeoutError(request=_FAKE_REQUEST))
    client = AnthropicAgentClient(client=fake_sdk_client)

    with pytest.raises(AnthropicTimeoutError):
        client.complete("system", "user", max_tokens=100)


def test_api_error_raises_anthropic_api_error() -> None:
    """A generic anthropic.APIError should be translated to AnthropicAPIError."""
    error = anthropic.APIConnectionError(message="connection failed", request=_FAKE_REQUEST)
    fake_sdk_client = _FakeAnthropicSDKClient(error=error)
    client = AnthropicAgentClient(client=fake_sdk_client)

    with pytest.raises(AnthropicAPIError):
        client.complete("system", "user", max_tokens=100)
