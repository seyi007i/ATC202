"""Interactive command-line interface for the Simple Loan Calculator.

All ``input()``/``print()`` calls live here, parameterized as
``input_func``/``print_func`` so the loop can be driven with fake
callables in tests without monkeypatching ``builtins.input``. Every
:class:`~module6.models.LoanCalculatorError` is caught and rendered as a
friendly message - nothing propagates out of :func:`main_loop`.
"""

from __future__ import annotations

from typing import Callable

from module6.models import LoanCalculatorError, LoanResult
from module6.session import LoanCalculatorSession

_MENU_TEXT = (
    "\nSimple Loan Calculator\n"
    "  [C]alculate\n"
    "  [R]eset\n"
    "  [E]xit\n"
    "Choose an option: "
)


def display_menu(print_func: Callable[[str], None] = print) -> None:
    """Print the calculate / reset / exit menu options.

    Args:
        print_func: Callable used to emit output, injectable for tests.
    """
    print_func(_MENU_TEXT)


def prompt_for_loan_inputs(
    input_func: Callable[[str], str] = input,
) -> tuple[str, str, str, str]:
    """Prompt for principal, annual rate, term value, and term unit in turn.

    Args:
        input_func: Callable used to read each line, injectable for tests.

    Returns:
        A 4-tuple of raw strings: (principal, annual_rate, term_value,
        term_unit).
    """
    principal = input_func("Loan principal: ")
    annual_rate = input_func("Annual interest rate (%): ")
    term_value = input_func("Loan term (number): ")
    term_unit = input_func("Loan term unit (months/years): ")
    return principal, annual_rate, term_value, term_unit


def format_result(result: LoanResult) -> str:
    """Render a LoanResult as a human-readable, aligned summary block.

    Args:
        result: The LoanResult to render.

    Returns:
        A multi-line string with all currency values shown to 2 decimal
        places.
    """
    return (
        "\nResults\n"
        f"  Monthly payment: {result.monthly_payment:.2f}\n"
        f"  Total payment:   {result.total_payment:.2f}\n"
        f"  Total interest:  {result.total_interest:.2f}\n"
    )


def format_error(error: LoanCalculatorError) -> str:
    """Render a LoanCalculatorError as a clear, user-facing message.

    Args:
        error: The caught domain error.

    Returns:
        A single-line string describing what needs to be corrected,
        never a raw traceback.
    """
    return f"Error: {error}"


def run_calculate_flow(
    session: LoanCalculatorSession,
    input_func: Callable[[str], str] = input,
    print_func: Callable[[str], None] = print,
) -> None:
    """Run one 'calculate' menu iteration end-to-end.

    Prompts for inputs, calls session.calculate(), and prints either the
    formatted result or a graceful error message. Never lets a
    LoanCalculatorError propagate.

    Args:
        session: The active LoanCalculatorSession.
        input_func: Callable used for prompts, injectable for tests.
        print_func: Callable used for output, injectable for tests.
    """
    principal, annual_rate, term_value, term_unit = prompt_for_loan_inputs(input_func)
    try:
        result = session.calculate(principal, annual_rate, term_value, term_unit)
    except LoanCalculatorError as error:
        print_func(format_error(error))
        return
    print_func(format_result(result))


def main_loop(
    session: LoanCalculatorSession | None = None,
    input_func: Callable[[str], str] = input,
    print_func: Callable[[str], None] = print,
) -> None:
    """Run the interactive calculate/reset/exit menu until the user exits.

    Args:
        session: Session instance to use; a fresh LoanCalculatorSession()
            is created if None (injectable for tests).
        input_func: Callable used for all menu/prompt input.
        print_func: Callable used for all output.
    """
    if session is None:
        session = LoanCalculatorSession()

    while True:
        display_menu(print_func)
        choice = input_func("").strip().lower()
        if choice in ("c", "calculate"):
            run_calculate_flow(session, input_func, print_func)
        elif choice in ("r", "reset"):
            session.reset()
            print_func("Calculator has been reset.")
        elif choice in ("e", "exit"):
            print_func("Goodbye.")
            return
        else:
            print_func(f"Unrecognized option: {choice!r}. Please choose C, R, or E.")


def main() -> None:
    """Real entry point: runs main_loop() wired to real input()/print()."""
    main_loop()
