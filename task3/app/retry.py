"""Hand-rolled exponential backoff retry for the Anthropic API.

Retries are deliberately not delegated to the SDK: this module retries
only on timeout / connection / temporary-server-error conditions, using
an injectable ``sleep`` function so tests never block on real time.
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from app.models import (
    AnthropicConnectionError,
    AnthropicTemporaryError,
    AnthropicTimeoutError,
)

T = TypeVar("T")

DEFAULT_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    AnthropicTimeoutError,
    AnthropicConnectionError,
    AnthropicTemporaryError,
)


def call_with_backoff(
    func: Callable[[], T],
    *,
    max_retries: int,
    base_delay: float,
    sleep: Callable[[float], None] = time.sleep,
    retryable: tuple[type[Exception], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
) -> T:
    """Call ``func``, retrying with exponential backoff on retryable errors.

    The delay before the Nth retry is ``base_delay * 2**(N-1)`` (i.e.
    1s, 2s, 4s for the default ``base_delay=1.0``). Non-retryable
    exceptions propagate immediately without any delay.

    Args:
        func: A zero-argument callable to invoke.
        max_retries: Maximum number of retries after the first attempt.
        base_delay: Delay in seconds before the first retry.
        sleep: Function used to wait between retries (injectable for tests).
        retryable: Exception types that trigger a retry.

    Returns:
        Whatever ``func()`` returns on success.

    Raises:
        Exception: The last exception raised by ``func``, once retries
            are exhausted, or immediately if it is not retryable.
    """
    attempt = 0
    while True:
        try:
            return func()
        except retryable:
            if attempt >= max_retries:
                raise
            sleep(base_delay * (2**attempt))
            attempt += 1
