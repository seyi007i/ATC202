"""Tests for app.anthropic_client.AnthropicAgentClient.

This is the only test module that fakes the Anthropic SDK itself (no
mocking library — hand-rolled duck-typed fakes), so it can verify the
wrapper's exception translation and response parsing in isolation.
Every other test module fakes AnthropicAgentClient's own interface
instead (see tests/conftest.py's FakeAgentClient).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import anthropic
import httpx
import pytest

from app.anthropic_client import AnthropicAgentClient
from app.models import (
    AnthropicAPIError,
    AnthropicConnectionError,
    AnthropicTemporaryError,
    AnthropicTimeoutError,
    MalformedAgentOutputError,
)

_FAKE_REQUEST = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _fake_status_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_FAKE_REQUEST)


@dataclass
class _FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class _FakeToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class _FakeResponse:
    content: list[Any]
    stop_reason: str = "end_turn"


class _FakeMessages:
    """Stands in for anthropic.Anthropic().messages."""

    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error
        self.create_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.create_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return self._result


class _FakeAnthropicSDKClient:
    """Stands in for anthropic.Anthropic(), including with_options()."""

    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.messages = _FakeMessages(result, error)
        self.with_options_kwargs: dict[str, Any] | None = None

    def with_options(self, *, timeout: float, max_retries: int) -> "_FakeAnthropicSDKClient":
        self.with_options_kwargs = {"timeout": timeout, "max_retries": max_retries}
        return self


def _make_client(fake_sdk_client, **overrides) -> AnthropicAgentClient:
    kwargs = {"client": fake_sdk_client, "model": "test-model", "max_retries": 0, "sleep": lambda s: None}
    kwargs.update(overrides)
    return AnthropicAgentClient(**kwargs)


def test_disables_sdk_level_retries_and_applies_timeout():
    fake_sdk_client = _FakeAnthropicSDKClient(result=_FakeResponse(content=[_FakeTextBlock("hi")]))
    _make_client(fake_sdk_client, timeout=30.0)
    assert fake_sdk_client.with_options_kwargs == {"timeout": 30.0, "max_retries": 0}


def test_complete_returns_text_from_response():
    fake_sdk_client = _FakeAnthropicSDKClient(result=_FakeResponse(content=[_FakeTextBlock("Hello there")]))
    client = _make_client(fake_sdk_client)
    result = client.complete("system", "hi", max_tokens=100)
    assert result == "Hello there"


def test_complete_joins_multiple_text_blocks():
    fake_sdk_client = _FakeAnthropicSDKClient(
        result=_FakeResponse(content=[_FakeTextBlock("Part one."), _FakeTextBlock("Part two.")])
    )
    client = _make_client(fake_sdk_client)
    result = client.complete("system", "hi", max_tokens=100)
    assert result == "Part one.\nPart two."


def test_complete_raises_malformed_when_no_text_block():
    fake_sdk_client = _FakeAnthropicSDKClient(result=_FakeResponse(content=[]))
    client = _make_client(fake_sdk_client)
    with pytest.raises(MalformedAgentOutputError):
        client.complete("system", "hi", max_tokens=100)


def test_complete_with_tools_parses_tool_use_block():
    fake_sdk_client = _FakeAnthropicSDKClient(
        result=_FakeResponse(
            content=[_FakeToolUseBlock(id="call_1", name="fraud_red_flag_check", input={"message": "hi"})],
            stop_reason="tool_use",
        )
    )
    client = _make_client(fake_sdk_client)
    result = client.complete_with_tools("system", [], tools=[], max_tokens=100)
    assert result.text is None
    assert result.stop_reason == "tool_use"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "fraud_red_flag_check"
    assert result.tool_calls[0].input == {"message": "hi"}
    assert result.raw_content == [
        {"type": "tool_use", "id": "call_1", "name": "fraud_red_flag_check", "input": {"message": "hi"}}
    ]


def test_complete_with_tools_parses_plain_text_response():
    fake_sdk_client = _FakeAnthropicSDKClient(
        result=_FakeResponse(content=[_FakeTextBlock("All good.")], stop_reason="end_turn")
    )
    client = _make_client(fake_sdk_client)
    result = client.complete_with_tools("system", [], tools=[], max_tokens=100)
    assert result.text == "All good."
    assert result.tool_calls == []


def test_truncated_response_raises_malformed_output_error():
    fake_sdk_client = _FakeAnthropicSDKClient(
        result=_FakeResponse(content=[_FakeTextBlock("cut off")], stop_reason="max_tokens")
    )
    client = _make_client(fake_sdk_client)
    with pytest.raises(MalformedAgentOutputError, match="truncated"):
        client.complete_with_tools("system", [], tools=[], max_tokens=10)


def test_timeout_error_is_translated():
    fake_sdk_client = _FakeAnthropicSDKClient(error=anthropic.APITimeoutError(request=_FAKE_REQUEST))
    client = _make_client(fake_sdk_client)
    with pytest.raises(AnthropicTimeoutError):
        client.complete("system", "hi", max_tokens=100)


def test_connection_error_is_translated():
    error = anthropic.APIConnectionError(message="connection failed", request=_FAKE_REQUEST)
    fake_sdk_client = _FakeAnthropicSDKClient(error=error)
    client = _make_client(fake_sdk_client)
    with pytest.raises(AnthropicConnectionError):
        client.complete("system", "hi", max_tokens=100)


def test_rate_limit_error_is_translated_as_temporary():
    error = anthropic.RateLimitError("rate limited", response=_fake_status_response(429), body=None)
    fake_sdk_client = _FakeAnthropicSDKClient(error=error)
    client = _make_client(fake_sdk_client)
    with pytest.raises(AnthropicTemporaryError):
        client.complete("system", "hi", max_tokens=100)


def test_internal_server_error_is_translated_as_temporary():
    error = anthropic.InternalServerError("server error", response=_fake_status_response(500), body=None)
    fake_sdk_client = _FakeAnthropicSDKClient(error=error)
    client = _make_client(fake_sdk_client)
    with pytest.raises(AnthropicTemporaryError):
        client.complete("system", "hi", max_tokens=100)


def test_bad_request_error_is_translated_as_non_retryable_api_error():
    error = anthropic.BadRequestError("bad request", response=_fake_status_response(400), body=None)
    fake_sdk_client = _FakeAnthropicSDKClient(error=error)
    client = _make_client(fake_sdk_client)
    with pytest.raises(AnthropicAPIError):
        client.complete("system", "hi", max_tokens=100)


def test_retries_via_backoff_module_then_succeeds():
    attempts = {"count": 0}
    sleeps: list[float] = []

    class _FlakyMessages:
        def create(self, **kwargs):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise anthropic.APITimeoutError(request=_FAKE_REQUEST)
            return _FakeResponse(content=[_FakeTextBlock("recovered")])

    fake_sdk_client = _FakeAnthropicSDKClient()
    fake_sdk_client.messages = _FlakyMessages()

    client = AnthropicAgentClient(
        client=fake_sdk_client,
        model="test-model",
        max_retries=3,
        backoff_base=1.0,
        sleep=sleeps.append,
    )
    result = client.complete("system", "hi", max_tokens=100)
    assert result == "recovered"
    assert sleeps == [1.0, 2.0]
