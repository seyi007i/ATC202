"""Tests for the tool implementations in ``student_support_assistance.tools``."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from student_support_assistance.models import (
    EmptyQueryError,
    InvalidInputError,
    StudentNotFoundError,
    TicketWriteError,
)
from student_support_assistance.tools import (
    check_enrollment_status,
    escalate_to_advisor,
    search_knowledge_base,
)


class TestSearchKnowledgeBaseTool:
    """Tests for the search_knowledge_base tool wrapper."""

    def test_returns_list_of_dicts_with_expected_keys(self) -> None:
        """Each result dict must have question, answer, and score keys."""
        results = search_knowledge_base("How do I register for courses?")
        assert isinstance(results, list)
        assert results
        for entry in results:
            assert set(entry.keys()) == {"question", "answer", "score"}

    def test_empty_query_raises_empty_query_error(self) -> None:
        """An empty query must raise EmptyQueryError, not return []."""
        with pytest.raises(EmptyQueryError):
            search_knowledge_base("")

    def test_non_string_query_raises_invalid_input_error(self) -> None:
        """A non-string query must raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            search_knowledge_base(42)  # type: ignore[arg-type]


class TestCheckEnrollmentStatusTool:
    """Tests for the check_enrollment_status tool."""

    def test_known_student_returns_expected_shape(self) -> None:
        """A known student ID should return the documented dict shape."""
        result = check_enrollment_status("S1001")
        assert result == {
            "student_id": "S1001",
            "status": "Enrolled",
            "courses": ["Python Programming", "Data Structures"],
        }

    def test_lookup_is_case_insensitive(self) -> None:
        """Lowercase student IDs should resolve to the same record."""
        result = check_enrollment_status("s1001")
        assert result["student_id"] == "S1001"

    def test_unknown_student_raises_student_not_found_error(self) -> None:
        """An unknown student ID must raise StudentNotFoundError."""
        with pytest.raises(StudentNotFoundError):
            check_enrollment_status("S9999")

    def test_student_not_found_error_message_contains_id(self) -> None:
        """The raised error should reference the offending student ID."""
        with pytest.raises(StudentNotFoundError, match="S9999"):
            check_enrollment_status("S9999")

    def test_empty_student_id_raises_empty_query_error(self) -> None:
        """An empty student ID must raise EmptyQueryError."""
        with pytest.raises(EmptyQueryError):
            check_enrollment_status("")

    @pytest.mark.parametrize("bad_id", [None, 1001, ["S1001"]])
    def test_non_string_student_id_raises_invalid_input_error(self, bad_id: object) -> None:
        """Non-string student IDs must raise InvalidInputError."""
        with pytest.raises(InvalidInputError):
            check_enrollment_status(bad_id)  # type: ignore[arg-type]

    def test_student_with_no_courses_returns_empty_list(self) -> None:
        """A student on leave with no active courses returns an empty list."""
        result = check_enrollment_status("S1003")
        assert result["courses"] == []


class TestEscalateToAdvisorTool:
    """Tests for the escalate_to_advisor tool."""

    def test_creates_ticket_with_expected_shape(self, tmp_path: Path) -> None:
        """A successful escalation returns a ticket_id and created status."""
        tickets_file = tmp_path / "tickets.txt"
        result = escalate_to_advisor("S1001", "Tuition appeal", tickets_file=tickets_file)
        assert result["status"] == "created"
        assert uuid.UUID(result["ticket_id"])  # raises ValueError if not a valid UUID

    def test_appends_ticket_details_to_file(self, tmp_path: Path) -> None:
        """The ticket details must be appended to the given tickets file."""
        tickets_file = tmp_path / "tickets.txt"
        result = escalate_to_advisor("S1002", "Financial aid dispute", tickets_file=tickets_file)
        contents = tickets_file.read_text(encoding="utf-8")
        assert result["ticket_id"] in contents
        assert "S1002" in contents
        assert "Financial aid dispute" in contents

    def test_multiple_escalations_append_rather_than_overwrite(self, tmp_path: Path) -> None:
        """Successive escalations should both appear in the tickets file."""
        tickets_file = tmp_path / "tickets.txt"
        first = escalate_to_advisor("S1001", "First issue", tickets_file=tickets_file)
        second = escalate_to_advisor("S1001", "Second issue", tickets_file=tickets_file)
        contents = tickets_file.read_text(encoding="utf-8")
        assert first["ticket_id"] in contents
        assert second["ticket_id"] in contents

    def test_empty_student_id_raises_empty_query_error(self, tmp_path: Path) -> None:
        """An empty student ID must raise EmptyQueryError."""
        tickets_file = tmp_path / "tickets.txt"
        with pytest.raises(EmptyQueryError):
            escalate_to_advisor("", "Some issue", tickets_file=tickets_file)

    def test_empty_query_summary_raises_empty_query_error(self, tmp_path: Path) -> None:
        """An empty query summary must raise EmptyQueryError."""
        tickets_file = tmp_path / "tickets.txt"
        with pytest.raises(EmptyQueryError):
            escalate_to_advisor("S1001", "", tickets_file=tickets_file)

    @pytest.mark.parametrize("bad_value", [None, 42, ["oops"]])
    def test_non_string_arguments_raise_invalid_input_error(
        self, tmp_path: Path, bad_value: object
    ) -> None:
        """Non-string student_id or query_summary must raise InvalidInputError."""
        tickets_file = tmp_path / "tickets.txt"
        with pytest.raises(InvalidInputError):
            escalate_to_advisor(bad_value, "Some issue", tickets_file=tickets_file)  # type: ignore[arg-type]
        with pytest.raises(InvalidInputError):
            escalate_to_advisor("S1001", bad_value, tickets_file=tickets_file)  # type: ignore[arg-type]

    def test_file_io_error_raises_ticket_write_error(self, tmp_path: Path) -> None:
        """Writing to an unwritable location must raise TicketWriteError."""
        unwritable_dir_as_file_target = tmp_path / "not_a_directory"
        unwritable_dir_as_file_target.write_text("occupied", encoding="utf-8")
        bad_path = unwritable_dir_as_file_target / "tickets.txt"
        with pytest.raises(TicketWriteError):
            escalate_to_advisor("S1001", "Some issue", tickets_file=bad_path)
