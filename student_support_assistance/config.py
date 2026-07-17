"""Centralized, configurable constants for the Student Support Assistant.

Keeping tunables in one module makes behavior (search depth, file
locations, logging verbosity, ID formats) adjustable without touching
business logic in other modules.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

#: Number of top FAQ matches returned by the knowledge base search tool.
TOP_K_RESULTS: int = 3

#: Minimum Jaccard/similarity score for an FAQ entry to be considered a
#: match at all. Entries below this are excluded even if there are fewer
#: than TOP_K_RESULTS candidates, so the agent never claims an unrelated
#: FAQ is relevant.
MIN_RELEVANCE_SCORE: float = 0.01

#: Weight given to token-overlap (Jaccard) similarity vs. sequence-based
#: similarity when scoring an FAQ entry against a query.
JACCARD_WEIGHT: float = 0.7
SEQUENCE_WEIGHT: float = 1.0 - JACCARD_WEIGHT

#: Directory the project lives in, used to resolve data file paths.
BASE_DIR: Path = Path(__file__).resolve().parent

#: File that escalation tickets are appended to.
SUPPORT_TICKETS_FILE: Path = BASE_DIR / "support_tickets.txt"

#: Regex used by the agent to opportunistically pull a student ID out of a
#: free-text user message (e.g. "check enrollment for student S1001").
STUDENT_ID_SEARCH_PATTERN: re.Pattern[str] = re.compile(r"\bS\d{4,}\b", re.IGNORECASE)

#: Name of the shared application logger.
LOGGER_NAME: str = "student_support_assistance"

#: Default logging level for the application logger.
LOG_LEVEL: int = logging.INFO

#: Keywords that route a user message to the escalation tool.
ESCALATION_KEYWORDS: tuple[str, ...] = (
    "appeal",
    "complaint",
    "complain",
    "dispute",
    "human advisor",
    "human",
    "advisor",
    "speak to someone",
    "escalate",
    "financial aid dispute",
    "special request",
    "technical issue",
    "not working",
    "frustrated",
    "unhappy",
    "unfair",
)

#: Keywords that route a user message to the enrollment-status tool.
ENROLLMENT_KEYWORDS: tuple[str, ...] = (
    "enroll",
    "enrolled",
    "enrollment",
    "my courses",
    "my classes",
    "am i registered",
    "show my classes",
    "what courses am i taking",
    "class schedule",
    "my schedule",
)
