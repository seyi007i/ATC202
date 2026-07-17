"""Centralized, configurable constants for the document pipeline.

Keeping tunables in one module makes model choice, token/timeout budgets,
and supported formats adjustable without touching business logic elsewhere.
"""

from __future__ import annotations

import logging

#: Claude model used for every agent call.
MODEL: str = "claude-sonnet-5"

#: Per-call max_tokens budgets, sized to each agent's expected output size.
#: Extraction/analysis echo substantial document content back verbatim, so
#: they get the largest budget the Anthropic SDK allows without requiring
#: streaming (requests above this may hit the SDK's 10-minute non-streaming
#: cap). Very long source documents can still exceed this and raise
#: MalformedAgentOutputError due to truncation - see the README's
#: "Known Limitations" section.
EXTRACTION_MAX_TOKENS: int = 8192
ANALYSIS_MAX_TOKENS: int = 8192
SYNTHESIS_MAX_TOKENS: int = 4096

#: Target maximum character length of a single extraction chunk's raw text.
#: Documents longer than this are split (on paragraph boundaries, see
#: document_pipeline.chunking) into multiple chunks, each extracted
#: independently and merged, so a single chunk's echoed-verbatim JSON
#: output stays comfortably under EXTRACTION_MAX_TOKENS.
EXTRACTION_CHUNK_MAX_CHARS: int = 20000

#: Per-request timeout, in seconds, for calls to the Anthropic API.
REQUEST_TIMEOUT_SECONDS: float = 120.0

#: Retry count for transient Anthropic API failures.
MAX_RETRIES: int = 2

#: Valid inclusive bounds for any confidence score in agent output.
MIN_CONFIDENCE: float = 0.0
MAX_CONFIDENCE: float = 1.0

#: File extensions load_document_text() knows how to read.
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md", ".pdf", ".docx"})

#: Name of the shared application logger.
LOGGER_NAME: str = "document_pipeline"

#: Default logging level for the application logger.
LOG_LEVEL: int = logging.INFO
