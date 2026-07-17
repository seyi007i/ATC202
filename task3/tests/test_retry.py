"""Tests for app.retry.call_with_backoff.

All tests inject a recording fake ``sleep`` so none of them actually
block for real seconds.
"""

from __future__ import annotations

import pytest

from app.models import AnthropicTimeoutError, InvalidInputError
from app.retry import call_with_backoff


def test_returns_result_on_first_success():
    sleeps: list[float] = []
    result = call_with_backoff(
        lambda: "ok", max_retries=3, base_delay=1.0, sleep=sleeps.append
    )
    assert result == "ok"
    assert sleeps == []


def test_retries_then_succeeds_with_correct_backoff_schedule():
    attempts = {"count": 0}
    sleeps: list[float] = []

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise AnthropicTimeoutError("timed out")
        return "recovered"

    result = call_with_backoff(flaky, max_retries=3, base_delay=1.0, sleep=sleeps.append)

    assert result == "recovered"
    assert sleeps == [1.0, 2.0]


def test_exhausts_retries_and_raises():
    sleeps: list[float] = []

    def always_fails():
        raise AnthropicTimeoutError("still timing out")

    with pytest.raises(AnthropicTimeoutError):
        call_with_backoff(always_fails, max_retries=3, base_delay=1.0, sleep=sleeps.append)

    assert sleeps == [1.0, 2.0, 4.0]


def test_non_retryable_exception_skips_retry_entirely():
    sleeps: list[float] = []
    calls = {"count": 0}

    def raises_invalid_input():
        calls["count"] += 1
        raise InvalidInputError("bad input")

    with pytest.raises(InvalidInputError):
        call_with_backoff(raises_invalid_input, max_retries=3, base_delay=1.0, sleep=sleeps.append)

    assert calls["count"] == 1
    assert sleeps == []


def test_zero_max_retries_raises_immediately_on_first_failure():
    sleeps: list[float] = []

    def always_fails():
        raise AnthropicTimeoutError("nope")

    with pytest.raises(AnthropicTimeoutError):
        call_with_backoff(always_fails, max_retries=0, base_delay=1.0, sleep=sleeps.append)

    assert sleeps == []
