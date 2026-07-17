"""Thin wrapper around the Anthropic SDK with retry/backoff integration.

The Anthropic SDK's own retry mechanism is explicitly disabled
(``max_retries=0``) so that :mod:`app.retry` is the single source of
retry behavior, matching the project's 1s/2s/4s backoff requirement.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import anthropic

from app import config
from app.models import (
    AgentTurnResult,
    AnthropicAPIError,
    AnthropicConnectionError,
    AnthropicTemporaryError,
    AnthropicTimeoutError,
    MalformedAgentOutputError,
    ToolCall,
)
from app.retry import call_with_backoff


class AnthropicAgentClient:
    """Calls the Anthropic Messages API with retry, timeout, and parsing."""

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        *,
        model: str = config.MAIN_MODEL,
        timeout: float = config.REQUEST_TIMEOUT_SECONDS,
        max_retries: int = config.MAX_RETRIES,
        backoff_base: float = config.RETRY_BACKOFF_BASE_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Build a client.

        Args:
            client: An existing ``anthropic.Anthropic`` instance (or a
                test fake exposing the same ``messages.create`` /
                ``with_options`` surface). Defaults to a real SDK client
                reading ``ANTHROPIC_API_KEY`` from the environment.
            model: The Claude model id to use for this client's calls.
            timeout: Per-request timeout in seconds.
            max_retries: Maximum retries performed by :mod:`app.retry`.
            backoff_base: Base delay in seconds for exponential backoff.
            sleep: Sleep function used between retries (injectable).
        """
        base_client = client if client is not None else anthropic.Anthropic()
        self._client = base_client.with_options(timeout=timeout, max_retries=0)
        self.model = model
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._sleep = sleep

    def complete(self, system_prompt: str, user_message: str, *, max_tokens: int) -> str:
        """Send a single-turn request and return the assistant's text.

        Args:
            system_prompt: The system prompt for this call.
            user_message: The user message content.
            max_tokens: Maximum tokens to generate.

        Returns:
            The assistant's text reply.

        Raises:
            MalformedAgentOutputError: If the response has no text.
            app.models.SafeBankError: On API failure after retries.
        """
        messages = [{"role": "user", "content": user_message}]

        def _call() -> Any:
            return self._send_once(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            )

        response = call_with_backoff(
            _call,
            max_retries=self._max_retries,
            base_delay=self._backoff_base,
            sleep=self._sleep,
        )
        turn = self._normalize_response(response)
        if turn.text is None:
            raise MalformedAgentOutputError(
                "Anthropic response contained no text content block."
            )
        return turn.text

    def complete_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> AgentTurnResult:
        """Send a multi-turn, tool-enabled request.

        Args:
            system_prompt: The system prompt for this call.
            messages: The full conversation transcript so far, in the
                Anthropic Messages API format.
            tools: Tool schemas to expose to the model.
            max_tokens: Maximum tokens to generate.

        Returns:
            A normalized :class:`app.models.AgentTurnResult`.

        Raises:
            MalformedAgentOutputError: If the response was truncated.
            app.models.SafeBankError: On API failure after retries.
        """

        def _call() -> Any:
            return self._send_once(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                tools=tools,
            )

        response = call_with_backoff(
            _call,
            max_retries=self._max_retries,
            base_delay=self._backoff_base,
            sleep=self._sleep,
        )
        return self._normalize_response(response)

    def _send_once(self, **kwargs: Any) -> Any:
        """Issue one request to the SDK, translating exceptions.

        Raises:
            AnthropicTimeoutError: On request timeout (retryable).
            AnthropicConnectionError: On network failure (retryable).
            AnthropicTemporaryError: On 429/5xx responses (retryable).
            AnthropicAPIError: On any other API error (not retryable).
        """
        try:
            return self._client.messages.create(**kwargs)
        except anthropic.APITimeoutError as exc:
            raise AnthropicTimeoutError(str(exc)) from exc
        except anthropic.APIConnectionError as exc:
            raise AnthropicConnectionError(str(exc)) from exc
        except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
            raise AnthropicTemporaryError(str(exc)) from exc
        except anthropic.APIError as exc:
            raise AnthropicAPIError(str(exc)) from exc

    @staticmethod
    def _normalize_response(response: Any) -> AgentTurnResult:
        """Convert an SDK (or fake) response into an ``AgentTurnResult``.

        Raises:
            MalformedAgentOutputError: If the response was truncated
                because it hit the ``max_tokens`` limit.
        """
        if response.stop_reason == "max_tokens":
            raise MalformedAgentOutputError(
                "Anthropic response was truncated after reaching the max_tokens limit."
            )

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        raw_content: list[dict[str, Any]] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                raw_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))
                raw_content.append(
                    {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
                )

        text = "\n".join(text_parts) if text_parts else None
        return AgentTurnResult(
            text=text,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            raw_content=raw_content,
        )
