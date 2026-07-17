"""Tests for module6.cli, driven via fake input_func/print_func callables
(no monkeypatching of builtins.input/print)."""

from __future__ import annotations

from module6.cli import (
    display_menu,
    format_error,
    format_result,
    main_loop,
    prompt_for_loan_inputs,
    run_calculate_flow,
)
from module6.models import EmptyInputError
from module6.session import LoanCalculatorSession


def _make_input(responses: list[str]):
    """Build an input_func that yields each response from responses in turn."""
    queue = iter(responses)

    def _input(_prompt: str = "") -> str:
        return next(queue)

    return _input


def _make_print():
    """Build a print_func that records every message into a list."""
    lines: list[str] = []

    def _print(message: str) -> None:
        lines.append(message)

    return _print, lines


class TestDisplayMenu:
    """Tests for display_menu()."""

    def test_prints_menu_once(self) -> None:
        """display_menu emits exactly one message containing all options."""
        print_func, lines = _make_print()
        display_menu(print_func)
        assert len(lines) == 1
        assert "[C]alculate" in lines[0]
        assert "[R]eset" in lines[0]
        assert "[E]xit" in lines[0]


class TestPromptForLoanInputs:
    """Tests for prompt_for_loan_inputs()."""

    def test_returns_inputs_in_order(self) -> None:
        """The four raw values are read and returned in the documented order."""
        input_func = _make_input(["100000", "5", "30", "years"])
        result = prompt_for_loan_inputs(input_func)
        assert result == ("100000", "5", "30", "years")


class TestFormatResult:
    """Tests for format_result()."""

    def test_shows_two_decimal_places(self) -> None:
        """Every monetary value in the formatted output has 2 decimal places."""
        from decimal import Decimal

        from module6.models import LoanResult

        result = LoanResult(
            principal=Decimal("12000"),
            annual_rate=Decimal("0"),
            term_months=12,
            monthly_payment=Decimal("1000.00"),
            total_payment=Decimal("12000.00"),
            total_interest=Decimal("0.00"),
        )
        text = format_result(result)
        assert "1000.00" in text
        assert "12000.00" in text
        assert "0.00" in text


class TestFormatError:
    """Tests for format_error()."""

    def test_includes_error_prefix_and_message(self) -> None:
        """The formatted error is a clear, single-line, user-facing message."""
        error = EmptyInputError("Loan principal is required and cannot be empty.")
        text = format_error(error)
        assert text.startswith("Error:")
        assert "Loan principal is required and cannot be empty." in text


class TestRunCalculateFlow:
    """Tests for run_calculate_flow()."""

    def test_valid_inputs_prints_result(self) -> None:
        """A valid set of inputs prints a formatted result, not an error."""
        session = LoanCalculatorSession()
        input_func = _make_input(["12000", "0", "12", "months"])
        print_func, lines = _make_print()
        run_calculate_flow(session, input_func, print_func)
        assert any("1000.00" in line for line in lines)
        assert session.has_result() is True

    def test_invalid_input_prints_error_and_does_not_raise(self) -> None:
        """An invalid input prints a graceful error message instead of
        letting the exception propagate."""
        session = LoanCalculatorSession()
        input_func = _make_input(["abc", "5", "12", "months"])
        print_func, lines = _make_print()
        run_calculate_flow(session, input_func, print_func)
        assert any(line.startswith("Error:") for line in lines)
        assert session.has_result() is False


class TestMainLoop:
    """Tests for the full interactive main_loop() (TC-014, TC-015)."""

    def test_calculate_reset_calculate_exit_flow_handles_errors_gracefully(self) -> None:
        """TC-015-style flow: calculate, hit an invalid input, reset, and
        calculate again, then exit -- the loop must never crash."""
        responses = [
            "c", "100000", "5", "20", "years",   # valid calculation
            "c", "abc", "5", "12", "months",       # invalid principal
            "r",                                    # reset (TC-014)
            "c", "12000", "0", "12", "months",     # valid calculation again
            "e",                                     # exit
        ]
        input_func = _make_input(responses)
        print_func, lines = _make_print()
        session = LoanCalculatorSession()

        main_loop(session, input_func, print_func)

        assert any("659.96" in line for line in lines)
        assert any(line.startswith("Error:") for line in lines)
        assert any("reset" in line.lower() for line in lines)
        assert any("1000.00" in line for line in lines)
        assert any("Goodbye" in line for line in lines)
        # Final state reflects the last successful calculation, not a crash.
        assert session.has_result() is True

    def test_unrecognized_option_reprompts_without_crashing(self) -> None:
        """An unrecognized menu choice prints a message and the loop
        continues instead of crashing."""
        input_func = _make_input(["x", "e"])
        print_func, lines = _make_print()
        main_loop(LoanCalculatorSession(), input_func, print_func)
        assert any("Unrecognized option" in line for line in lines)
        assert any("Goodbye" in line for line in lines)

    def test_exit_terminates_loop_immediately(self) -> None:
        """Choosing exit on the first turn ends the loop right away."""
        input_func = _make_input(["e"])
        print_func, lines = _make_print()
        main_loop(LoanCalculatorSession(), input_func, print_func)
        assert lines[-1] == "Goodbye."

    def test_creates_default_session_when_none_given(self) -> None:
        """main_loop() creates its own session when none is injected."""
        input_func = _make_input(["e"])
        print_func, _ = _make_print()
        main_loop(None, input_func, print_func)
