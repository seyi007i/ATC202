"""Simulated escalation of high-risk fraud cases.

No real external system is contacted. A escalation "ticket" is a locally
generated id appended to a local JSONL file, standing in for whatever a
real bank's fraud-desk integration would be.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app import config
from app.models import EscalationRecord, EscalationWriteError, FraudAssessment
from app.redaction import redact_sensitive

_SUMMARY_CHAR_LIMIT = 2000


class EscalationStore:
    """Persists simulated escalation tickets to a local JSONL file."""

    def __init__(self, path: Path = config.ESCALATION_STORE_PATH) -> None:
        """Build a store writing to ``path``.

        Args:
            path: File path to append escalation records to.
        """
        self._path = path

    def create_escalation(
        self,
        session_id: str,
        assessment: FraudAssessment,
        summary_text: str,
    ) -> EscalationRecord:
        """Create and persist a simulated escalation ticket.

        Args:
            session_id: The chat session id being escalated.
            assessment: The fraud assessment that triggered escalation.
            summary_text: A human-readable summary of the case, redacted
                before being persisted.

        Returns:
            The created :class:`app.models.EscalationRecord`.

        Raises:
            EscalationWriteError: If the record cannot be persisted.
        """
        ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        record = EscalationRecord(
            ticket_id=ticket_id,
            session_id=session_id,
            risk_level=assessment.risk_level,
            summary=redact_sensitive(summary_text)[:_SUMMARY_CHAR_LIMIT],
            created_at=datetime.now(timezone.utc),
        )
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(record.model_dump_json() + "\n")
        except OSError as exc:
            raise EscalationWriteError(f"Could not persist escalation record: {exc}") from exc
        return record
