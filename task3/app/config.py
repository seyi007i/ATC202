"""Application configuration loaded from environment variables.

All settings are plain module-level constants populated once at import
time via ``python-dotenv``. Nothing in this module performs network I/O.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR: Path = Path(__file__).resolve().parent.parent

ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")

MAIN_MODEL: str = os.getenv("SAFEBANK_MAIN_MODEL", "claude-sonnet-5")
SUBAGENT_MODEL: str = os.getenv("SAFEBANK_SUBAGENT_MODEL", "claude-sonnet-4-5-20250929")

REQUEST_TIMEOUT_SECONDS: float = float(os.getenv("SAFEBANK_REQUEST_TIMEOUT_SECONDS", "30"))
MAX_RETRIES: int = int(os.getenv("SAFEBANK_MAX_RETRIES", "3"))
RETRY_BACKOFF_BASE_SECONDS: float = float(os.getenv("SAFEBANK_RETRY_BACKOFF_BASE_SECONDS", "1"))

MAX_AGENT_STEPS: int = int(os.getenv("SAFEBANK_MAX_AGENT_STEPS", "6"))
SUMMARIZE_AFTER_TURNS: int = int(os.getenv("SAFEBANK_SUMMARIZE_AFTER_TURNS", "10"))

MAIN_MAX_TOKENS: int = int(os.getenv("SAFEBANK_MAIN_MAX_TOKENS", "1024"))
SUBAGENT_MAX_TOKENS: int = int(os.getenv("SAFEBANK_SUBAGENT_MAX_TOKENS", "1024"))
SUMMARY_MAX_TOKENS: int = int(os.getenv("SAFEBANK_SUMMARY_MAX_TOKENS", "512"))

ESCALATION_STORE_PATH: Path = Path(
    os.getenv("SAFEBANK_ESCALATION_STORE", str(BASE_DIR / "escalations.jsonl"))
)

MIN_CONFIDENCE: float = 0.0
MAX_CONFIDENCE: float = 1.0


def require_api_key() -> str:
    """Return the configured Anthropic API key or raise a friendly error.

    Raises:
        app.models.MissingAPIKeyError: If ``ANTHROPIC_API_KEY`` is unset or blank.
    """
    from app.models import MissingAPIKeyError

    if not ANTHROPIC_API_KEY or not ANTHROPIC_API_KEY.strip():
        raise MissingAPIKeyError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add "
            "your Anthropic API key before starting SafeBank Companion."
        )
    return ANTHROPIC_API_KEY
