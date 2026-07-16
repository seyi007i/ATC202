"""Thin wrapper around the Anthropic API used by every agent.

Centralizes model/timeout/retry configuration and translates the Anthropic
SDK's exceptions into this project's own exception types. Every agent module
depends on this wrapper's interface (not on ``anthropic`` directly), which is
the seam tests substitute a fake client through.
"""

from __future__ import annotations

import anthropic

from document_pipeline import config
from document_pipeline.models import AnthropicAPIError, AnthropicTimeoutError, MalformedAgentOutputError
from document_pipeline.utils import setup_logging

logger = setup_logging()


class AnthropicAgentClient:
    """Sends single system+user turns to a Claude model.

    Attributes:
        model: The Claude model ID used for every ``complete`` call.
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        *,
        model: str = config.MODEL,
        timeout: float = config.REQUEST_TIMEOUT_SECONDS,
        max_retries: int = config.MAX_RETRIES,
    ) -> None:
        """Initialize the wrapper, defaulting to a real Anthropic client.

        Args:
            client: An optional pre-built ``anthropic.Anthropic`` instance.
                Defaults to a fresh ``anthropic.Anthropic()``, which reads
                credentials from the ``ANTHROPIC_API_KEY`` environment variable.
            model: Claude model ID to use for ``complete`` calls.
            timeout: Per-request timeout, in seconds.
            max_retries: Retry count for transient errors.
        """
        base_client = client if client is not None else anthropic.Anthropic()
        self._client = base_client.with_options(timeout=timeout, max_retries=max_retries)
        self.model = model

    def complete(self, system_prompt: str, user_message: str, *, max_tokens: int) -> str:
        """Send one system+user turn and return the first text content block.

        Args:
            system_prompt: The system prompt for this call.
            user_message: The user-turn message content.
            max_tokens: The maximum number of tokens to generate.

        Returns:
            The text of the response's first text content block.

        Raises:
            AnthropicTimeoutError: If the request times out.
            AnthropicAPIError: If the Anthropic API returns any other error.
            MalformedAgentOutputError: If the response contains no text block,
                or was truncated before completing (``stop_reason == "max_tokens"``).
        """
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APITimeoutError as exc:
            logger.warning("Anthropic request timed out: %s", exc)
            raise AnthropicTimeoutError(str(exc)) from exc
        except anthropic.APIError as exc:
            logger.warning("Anthropic API error: %s", exc)
            raise AnthropicAPIError(str(exc)) from exc

        if response.stop_reason == "max_tokens":
            raise MalformedAgentOutputError(
                f"Anthropic response was truncated after reaching the {max_tokens}-token "
                "limit for this call, before completing its JSON output. Increase the "
                "relevant *_MAX_TOKENS constant in document_pipeline.config, or shorten "
                "the input."
            )

        text = next((block.text for block in response.content if block.type == "text"), None)
        if not text:
            raise MalformedAgentOutputError("Anthropic response contained no text content block.")
        return text
