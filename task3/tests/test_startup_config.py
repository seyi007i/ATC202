"""Tests for fail-fast startup behavior when ANTHROPIC_API_KEY is missing."""

from __future__ import annotations

import asyncio

import pytest

from app import config
from app.models import MissingAPIKeyError


def test_require_api_key_raises_when_missing(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", None)
    with pytest.raises(MissingAPIKeyError):
        config.require_api_key()


def test_require_api_key_raises_when_blank(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "   ")
    with pytest.raises(MissingAPIKeyError):
        config.require_api_key()


def test_require_api_key_returns_key_when_present(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "sk-ant-abc123")
    assert config.require_api_key() == "sk-ant-abc123"


def test_lifespan_exits_cleanly_when_api_key_missing(monkeypatch):
    from app import config as config_module
    from app.main import app as fastapi_app
    from app.main import lifespan

    monkeypatch.setattr(config_module, "ANTHROPIC_API_KEY", None)

    async def _run() -> None:
        async with lifespan(fastapi_app):
            pass  # pragma: no cover - should never be reached

    with pytest.raises(SystemExit):
        asyncio.run(_run())
