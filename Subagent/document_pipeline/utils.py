"""Shared logging setup for the document pipeline."""

from __future__ import annotations

import logging

from document_pipeline import config


def setup_logging(level: int = config.LOG_LEVEL) -> logging.Logger:
    """Configure and return the shared application logger.

    Idempotent: calling this repeatedly will not add duplicate handlers.

    Args:
        level: The logging level to set on the logger.

    Returns:
        The configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(config.LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    return logger
