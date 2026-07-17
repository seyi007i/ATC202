"""Tool implementations exposed to the Student Support Assistant agent.

Each function here is a self-contained "tool" in the Agent SDK sense: a
plain, well-documented Python callable with validated inputs and a
JSON-serializable return value, which :mod:`agent` selects and invokes
based on user intent.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from student_support_assistance import config
from student_support_assistance.knowledge_base import search_faqs
from student_support_assistance.models import (
    EscalationTicket,
    StudentNotFoundError,
    TicketWriteError,
)
from student_support_assistance.data import STUDENT_RECORDS
from student_support_assistance.utils import require_non_empty_string, setup_logging

logger = setup_logging()


def search_knowledge_base(query: str) -> list[dict[str, Any]]:
    """Search the FAQ knowledge base for entries relevant to ``query``.

    Use this whenever a user asks a general, policy, tuition, deadline,
    registration, campus, admissions, payment, or graduation question.

    Args:
        query: The user's natural-language question.

    Returns:
        A list of up to three dicts, each shaped
        ``{"question": str, "answer": str, "score": float}``, sorted by
        descending relevance.

    Raises:
        InvalidInputError: If ``query`` is not a string.
        EmptyQueryError: If ``query`` is empty or whitespace-only.
    """
    logger.info("search_knowledge_base called with query=%r", query)
    results = search_faqs(query)
    return [result.to_dict() for result in results]


def check_enrollment_status(student_id: str) -> dict[str, Any]:
    """Look up a student's enrollment status and current course list.

    Use this whenever a user asks about their enrollment, courses, or
    class schedule, and has supplied a student ID.

    Args:
        student_id: The student's unique identifier, e.g. "S1001".

    Returns:
        A dict shaped ``{"student_id": str, "status": str,
        "courses": list[str]}``.

    Raises:
        InvalidInputError: If ``student_id`` is not a non-empty string.
        StudentNotFoundError: If no record exists for ``student_id``.
    """
    logger.info("check_enrollment_status called with student_id=%r", student_id)
    clean_id = require_non_empty_string(student_id, "student_id").upper()

    record = STUDENT_RECORDS.get(clean_id)
    if record is None:
        logger.warning("Unknown student_id=%r", clean_id)
        raise StudentNotFoundError(clean_id)

    return record.to_dict()


def escalate_to_advisor(
    student_id: str,
    query_summary: str,
    tickets_file: Path | None = None,
) -> dict[str, Any]:
    """Escalate a request to a human advisor by opening a support ticket.

    Use this for complaints, appeals, financial aid disputes, special
    requests, technical issues requiring staff, or explicit requests to
    speak with a human advisor.

    Args:
        student_id: The student's unique identifier, e.g. "S1001".
        query_summary: A short description of the unresolved request.
        tickets_file: Path to append the ticket record to. Injectable so
            tests can redirect writes to a temporary file. Defaults to
            :data:`config.SUPPORT_TICKETS_FILE`, resolved at call time
            (not import time) so it honors runtime config changes.

    Returns:
        A dict shaped ``{"ticket_id": str, "status": "created"}``.

    Raises:
        InvalidInputError: If either argument is not a non-empty string.
        TicketWriteError: If the ticket cannot be written to disk.
    """
    logger.info(
        "escalate_to_advisor called with student_id=%r, query_summary=%r",
        student_id,
        query_summary,
    )
    if tickets_file is None:
        tickets_file = config.SUPPORT_TICKETS_FILE
    clean_id = require_non_empty_string(student_id, "student_id").upper()
    clean_summary = require_non_empty_string(query_summary, "query_summary")

    ticket = EscalationTicket(
        ticket_id=str(uuid.uuid4()),
        student_id=clean_id,
        query_summary=clean_summary,
    )

    try:
        with open(tickets_file, "a", encoding="utf-8") as handle:
            handle.write(
                f"ticket_id={ticket.ticket_id} | student_id={ticket.student_id} "
                f"| status={ticket.status} | query_summary={ticket.query_summary}\n"
            )
    except OSError as exc:
        logger.error("Failed to write ticket %s: %s", ticket.ticket_id, exc)
        raise TicketWriteError(
            f"Could not save escalation ticket to '{tickets_file}': {exc}"
        ) from exc

    logger.info("Created escalation ticket %s for %s", ticket.ticket_id, clean_id)
    return ticket.to_dict()
