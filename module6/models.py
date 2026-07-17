"""Data models and structured exceptions for the Simple Loan Calculator.

All cross-module data contracts live here as immutable dataclasses, and
every validation failure has its own named exception, so that
``calculator``, ``session``, ``cli``, and tests share a single source of
truth for shapes and error semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class LoanCalculatorError(Exception):
    """Base class for all loan-calculator domain errors.

    Catching this (instead of bare ``Exception``) lets the CLI distinguish
    expected, user-facing input/calculation failures from genuine bugs.
    """


class ValidationError(LoanCalculatorError):
    """Base class for all input-validation failures."""


class EmptyInputError(ValidationError):
    """Raised when a required field is empty or whitespace-only.

    Covers empty principal, interest rate, term value, or term unit.
    """


class NonNumericInputError(ValidationError):
    """Raised when a field that must be numeric cannot be parsed as one.

    Covers a non-numeric principal, interest rate, or term value (e.g.
    "abc" or "five").
    """


class PrincipalOutOfRangeError(ValidationError):
    """Raised when the loan principal is not greater than zero, or exceeds
    :data:`module6.config.MAX_PRINCIPAL`.
    """


class InterestRateOutOfRangeError(ValidationError):
    """Raised when the annual interest rate is outside the inclusive
    range [:data:`module6.config.MIN_INTEREST_RATE`,
    :data:`module6.config.MAX_INTEREST_RATE`].
    """


class InvalidTermValueError(ValidationError):
    """Raised when the term value is not a positive whole number.

    Covers a zero/negative term value and a non-integer term value (e.g.
    "12.5").
    """


class InvalidTermUnitError(ValidationError):
    """Raised when the term unit is neither "months" nor "years"
    (case-insensitive).
    """


class TermOutOfRangeError(ValidationError):
    """Raised when the normalized total term, in months, falls outside
    [:data:`module6.config.MIN_TERM_MONTHS`,
    :data:`module6.config.MAX_TERM_MONTHS`] (1 to 300 months, i.e. 25
    years).
    """


class CalculationError(LoanCalculatorError):
    """Raised when amortization arithmetic fails unexpectedly.

    Lets the CLI display a generic "unexpected error" message instead of
    crashing, for failures (e.g. a Decimal overflow) that validation did
    not already prevent.
    """


class TermUnit(str, Enum):
    """Unit for a loan's term value."""

    MONTHS = "months"
    YEARS = "years"


@dataclass(frozen=True)
class LoanResult:
    """The full result of a loan amortization calculation.

    Attributes:
        principal: The validated loan principal.
        annual_rate: The validated annual interest rate, as a percent
            (e.g. ``Decimal("5")`` for 5%).
        term_months: The normalized total term, in months.
        monthly_payment: The fixed monthly payment, rounded to 2 decimal
            places.
        total_payment: Total amount repaid over the loan's life, rounded
            to 2 decimal places.
        total_interest: Total interest paid over the loan's life, rounded
            to 2 decimal places.
    """

    principal: Decimal
    annual_rate: Decimal
    term_months: int
    monthly_payment: Decimal
    total_payment: Decimal
    total_interest: Decimal
