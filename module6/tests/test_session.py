"""Tests for module6.session.LoanCalculatorSession (FR-8 Reset)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from module6.models import EmptyInputError
from module6.session import LoanCalculatorSession


class TestLoanCalculatorSessionCalculate:
    """Tests for LoanCalculatorSession.calculate()."""

    def test_calculate_stores_raw_inputs_and_returns_result(self) -> None:
        """A successful calculation stores the raw inputs on the session
        and returns the computed LoanResult."""
        session = LoanCalculatorSession()
        result = session.calculate("12000", "0", "12", "months")
        assert session.principal == "12000"
        assert session.annual_rate == "0"
        assert session.term_value == "12"
        assert session.term_unit == "months"
        assert result.monthly_payment == Decimal("1000.00")

    def test_calculate_caches_result_on_last_result(self) -> None:
        """The computed result is cached on session.last_result."""
        session = LoanCalculatorSession()
        result = session.calculate("12000", "0", "12", "months")
        assert session.last_result is result

    def test_invalid_calculate_still_stores_raw_inputs_before_raising(self) -> None:
        """Even when validation fails, the raw inputs are recorded so the
        CLI can show what was entered."""
        session = LoanCalculatorSession()
        with pytest.raises(EmptyInputError):
            session.calculate("", "5", "12", "months")
        assert session.principal == ""
        assert session.last_result is None


class TestLoanCalculatorSessionReset:
    """Tests for LoanCalculatorSession.reset() (TC-014)."""

    def test_reset_clears_all_fields_to_none(self) -> None:
        """TC-014: reset() clears all inputs and the result back to None."""
        session = LoanCalculatorSession()
        session.calculate("12000", "0", "12", "months")
        session.reset()
        assert session.principal is None
        assert session.annual_rate is None
        assert session.term_value is None
        assert session.term_unit is None
        assert session.last_result is None

    def test_reset_on_fresh_session_is_a_no_op(self) -> None:
        """Resetting a session that never calculated anything is safe."""
        session = LoanCalculatorSession()
        session.reset()
        assert session.last_result is None


class TestLoanCalculatorSessionHasResult:
    """Tests for LoanCalculatorSession.has_result()."""

    def test_has_result_false_initially(self) -> None:
        """A freshly created session has no result yet."""
        assert LoanCalculatorSession().has_result() is False

    def test_has_result_true_after_calculate(self) -> None:
        """has_result() reflects a successful calculation."""
        session = LoanCalculatorSession()
        session.calculate("12000", "0", "12", "months")
        assert session.has_result() is True

    def test_has_result_false_after_reset(self) -> None:
        """has_result() returns to False after reset()."""
        session = LoanCalculatorSession()
        session.calculate("12000", "0", "12", "months")
        session.reset()
        assert session.has_result() is False
