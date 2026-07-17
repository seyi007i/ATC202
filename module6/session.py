"""Interactive session state for the Simple Loan Calculator CLI.

Holds the FR-8 "Reset" behavior as a plain, I/O-free object so it is
unit-testable without mocking stdin/stdout.
"""

from __future__ import annotations

from dataclasses import dataclass

from module6.calculator import calculate_loan
from module6.models import LoanResult


@dataclass
class LoanCalculatorSession:
    """Mutable session state for one interactive CLI run.

    Tracks the most recently entered raw inputs and the last successful
    result so the CLI can redisplay or clear them without any coupling
    to stdin/stdout.

    Attributes:
        principal: Last raw principal string entered, or None.
        annual_rate: Last raw interest-rate string entered, or None.
        term_value: Last raw term-value string entered, or None.
        term_unit: Last raw term-unit string entered, or None.
        last_result: The LoanResult of the most recent successful
            calculation, or None if none has succeeded yet (or after
            reset()).
    """

    principal: str | None = None
    annual_rate: str | None = None
    term_value: str | None = None
    term_unit: str | None = None
    last_result: LoanResult | None = None

    def calculate(
        self, principal: str, annual_rate: str, term_value: str, term_unit: str
    ) -> LoanResult:
        """Record the given raw inputs and run calculate_loan against them.

        Args:
            principal: Raw principal input.
            annual_rate: Raw annual interest rate input.
            term_value: Raw term value input.
            term_unit: Raw term unit input.

        Returns:
            The computed LoanResult (also cached on self.last_result).

        Raises:
            LoanCalculatorError: Any subclass raised by
                calculator.calculate_loan. Inputs are recorded on self
                before the calculation runs, so the CLI can still show
                what was entered even if validation fails.
        """
        self.principal = principal
        self.annual_rate = annual_rate
        self.term_value = term_value
        self.term_unit = term_unit
        result = calculate_loan(principal, annual_rate, term_value, term_unit)
        self.last_result = result
        return result

    def reset(self) -> None:
        """Clear all stored inputs and the last result back to initial state."""
        self.principal = None
        self.annual_rate = None
        self.term_value = None
        self.term_unit = None
        self.last_result = None

    def has_result(self) -> bool:
        """Return True if a calculation has succeeded since init or reset()."""
        return self.last_result is not None
