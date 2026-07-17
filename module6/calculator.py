"""Core validation and amortization logic for the Simple Loan Calculator.

Every function here is pure (no ``input()``/``print()``), so it can be
unit-tested by passing plain values directly - no stdin/stdout mocking
required. :func:`calculate_loan` is the single top-level orchestrator
that CLI (or any future) callers should use.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from module6 import config
from module6.models import (
    CalculationError,
    EmptyInputError,
    InterestRateOutOfRangeError,
    InvalidTermUnitError,
    InvalidTermValueError,
    LoanResult,
    NonNumericInputError,
    PrincipalOutOfRangeError,
    TermOutOfRangeError,
    TermUnit,
)


def _parse_decimal(raw_value: str | int | float | Decimal, field_name: str) -> Decimal:
    """Parse a raw value into a :class:`~decimal.Decimal`.

    Args:
        raw_value: A string (typically from a CLI prompt) or an already
            numeric value.
        field_name: Human-readable field name, used in error messages.

    Returns:
        The parsed value as a Decimal.

    Raises:
        EmptyInputError: If raw_value is an empty/whitespace-only string.
        NonNumericInputError: If raw_value cannot be parsed as a number.
    """
    if isinstance(raw_value, str):
        stripped = raw_value.strip()
        if not stripped:
            raise EmptyInputError(f"{field_name} is required and cannot be empty.")
        try:
            return Decimal(stripped)
        except InvalidOperation as exc:
            raise NonNumericInputError(
                f"{field_name} must be a valid number, got {raw_value!r}."
            ) from exc
    if isinstance(raw_value, (int, float, Decimal)):
        return Decimal(str(raw_value))
    raise NonNumericInputError(
        f"{field_name} must be numeric, got {type(raw_value).__name__}."
    )


def validate_principal(raw_principal: str | int | float | Decimal) -> Decimal:
    """Parse and validate a loan principal.

    Args:
        raw_principal: Raw value (typically a string from the CLI prompt,
            but numeric types are also accepted for programmatic callers).

    Returns:
        The validated principal as a Decimal, guaranteed
        ``0 < value <= config.MAX_PRINCIPAL``.

    Raises:
        EmptyInputError: If raw_principal is an empty/whitespace-only string.
        NonNumericInputError: If raw_principal cannot be parsed as a number.
        PrincipalOutOfRangeError: If the parsed value is <= 0 or
            > config.MAX_PRINCIPAL.
    """
    principal = _parse_decimal(raw_principal, "Loan principal")
    if principal <= 0 or principal > config.MAX_PRINCIPAL:
        raise PrincipalOutOfRangeError(
            "Loan principal must be greater than 0 and at most "
            f"{config.MAX_PRINCIPAL}, got {principal}."
        )
    return principal


def validate_interest_rate(raw_rate: str | int | float | Decimal) -> Decimal:
    """Parse and validate an annual interest rate (percent, decimals allowed).

    Args:
        raw_rate: Raw value for the annual interest rate.

    Returns:
        The validated rate as a Decimal, ``0 <= value <= 100``.

    Raises:
        EmptyInputError: If raw_rate is empty/whitespace-only.
        NonNumericInputError: If raw_rate cannot be parsed as a number.
        InterestRateOutOfRangeError: If the parsed value is outside
            [config.MIN_INTEREST_RATE, config.MAX_INTEREST_RATE].
    """
    rate = _parse_decimal(raw_rate, "Annual interest rate")
    if rate < config.MIN_INTEREST_RATE or rate > config.MAX_INTEREST_RATE:
        raise InterestRateOutOfRangeError(
            "Annual interest rate must be between "
            f"{config.MIN_INTEREST_RATE} and {config.MAX_INTEREST_RATE}, got {rate}."
        )
    return rate


def validate_term_value(raw_term_value: str | int | float) -> int:
    """Parse and validate the numeric term value (before unit is applied).

    Args:
        raw_term_value: Raw value, e.g. "12", "1.5", "-3".

    Returns:
        The validated term value as a positive int.

    Raises:
        EmptyInputError: If raw_term_value is empty/whitespace-only.
        NonNumericInputError: If raw_term_value cannot be parsed as a
            number at all.
        InvalidTermValueError: If the parsed number is not a positive
            integer (e.g. zero, negative, or has a fractional part such
            as 12.5).
    """
    parsed = _parse_decimal(raw_term_value, "Loan term value")
    if parsed <= 0 or parsed != parsed.to_integral_value():
        raise InvalidTermValueError(
            f"Loan term value must be a positive whole number, got {raw_term_value!r}."
        )
    return int(parsed)


def validate_term_unit(raw_unit: str) -> TermUnit:
    """Parse and validate the loan-term unit.

    Args:
        raw_unit: Raw string, expected to be "months" or "years"
            (case-insensitive, surrounding whitespace tolerated).

    Returns:
        The matching TermUnit enum member.

    Raises:
        EmptyInputError: If raw_unit is empty/whitespace-only.
        InvalidTermUnitError: If raw_unit is neither "months" nor "years".
    """
    if not isinstance(raw_unit, str) or not raw_unit.strip():
        raise EmptyInputError("Loan term unit is required and cannot be empty.")
    try:
        return TermUnit(raw_unit.strip().lower())
    except ValueError as exc:
        raise InvalidTermUnitError(
            f'Loan term unit must be "months" or "years", got {raw_unit!r}.'
        ) from exc


def normalize_term_to_months(term_value: int, term_unit: TermUnit) -> int:
    """Convert a validated term value and unit into a total month count.

    Args:
        term_value: Already-validated positive integer
            (validate_term_value output).
        term_unit: Already-validated TermUnit (validate_term_unit output).

    Returns:
        Total term length in months, guaranteed
        ``config.MIN_TERM_MONTHS <= months <= config.MAX_TERM_MONTHS``.

    Raises:
        TermOutOfRangeError: If the resulting month count is out of range
            (i.e. exceeds the 25-year maximum term).
    """
    total_months = (
        term_value * config.MONTHS_PER_YEAR if term_unit is TermUnit.YEARS else term_value
    )
    if not (config.MIN_TERM_MONTHS <= total_months <= config.MAX_TERM_MONTHS):
        raise TermOutOfRangeError(
            f"Loan term must be between {config.MIN_TERM_MONTHS} and "
            f"{config.MAX_TERM_MONTHS} months (1 month to 25 years), "
            f"got {total_months} months."
        )
    return total_months


def _round_currency(value: Decimal) -> Decimal:
    """Round a monetary value to exactly 2 decimal places (BR-5).

    Args:
        value: The raw monetary value to round.

    Returns:
        value quantized to 2 decimal places using ROUND_HALF_UP.

    Raises:
        CalculationError: If the value cannot be quantized.
    """
    try:
        return value.quantize(config.CURRENCY_QUANTIZE, rounding=ROUND_HALF_UP)
    except (InvalidOperation, OverflowError) as exc:
        raise CalculationError(f"Failed to round monetary value: {value}.") from exc


def calculate_monthly_payment(
    principal: Decimal, annual_rate: Decimal, total_months: int
) -> Decimal:
    """Compute the fixed monthly payment for an amortizing loan.

    Uses the standard formula ``M = P * r * (1+r)^n / ((1+r)^n - 1)``
    where ``r = (annual_rate/100)/12``, for ``annual_rate > 0``. For
    ``annual_rate == 0`` (BR-4), falls back to
    ``principal / total_months`` to avoid a 0/0 division in the standard
    formula.

    Args:
        principal: Validated principal (> 0).
        annual_rate: Validated annual rate percent (0 <= rate <= 100).
        total_months: Validated total term in months.

    Returns:
        The monthly payment as a Decimal, rounded to exactly 2 decimal
        places (BR-5).

    Raises:
        CalculationError: If an unexpected arithmetic failure occurs
            that validation did not already prevent.
    """
    try:
        if annual_rate == 0:
            monthly_payment = principal / total_months
        else:
            monthly_rate = (annual_rate / Decimal("100")) / config.MONTHS_PER_YEAR
            growth = (1 + monthly_rate) ** total_months
            monthly_payment = principal * monthly_rate * growth / (growth - 1)
    except (InvalidOperation, OverflowError, ZeroDivisionError) as exc:
        raise CalculationError(f"Failed to calculate monthly payment: {exc}.") from exc
    return _round_currency(monthly_payment)


def calculate_total_payment(monthly_payment: Decimal, total_months: int) -> Decimal:
    """Compute total amount repaid over the life of the loan.

    Args:
        monthly_payment: The rounded monthly payment.
        total_months: Total term in months.

    Returns:
        ``monthly_payment * total_months``, rounded to 2 decimal places.

    Raises:
        CalculationError: On an unexpected arithmetic failure.
    """
    try:
        total_payment = monthly_payment * total_months
    except (InvalidOperation, OverflowError) as exc:
        raise CalculationError(f"Failed to calculate total payment: {exc}.") from exc
    return _round_currency(total_payment)


def calculate_total_interest(total_payment: Decimal, principal: Decimal) -> Decimal:
    """Compute total interest paid over the life of the loan.

    Args:
        total_payment: The computed total payment.
        principal: The validated principal.

    Returns:
        ``total_payment - principal``, rounded to 2 decimal places.

    Raises:
        CalculationError: On an unexpected arithmetic failure.
    """
    try:
        total_interest = total_payment - principal
    except (InvalidOperation, OverflowError) as exc:
        raise CalculationError(f"Failed to calculate total interest: {exc}.") from exc
    return _round_currency(total_interest)


def calculate_loan(
    principal: str | int | float | Decimal,
    annual_rate: str | int | float | Decimal,
    term_value: str | int | float,
    term_unit: str | TermUnit,
) -> LoanResult:
    """Validate all raw inputs and compute the full loan amortization result.

    This is the single top-level orchestrator; it composes
    :func:`validate_principal`, :func:`validate_interest_rate`,
    :func:`validate_term_value`, :func:`validate_term_unit`,
    :func:`normalize_term_to_months`, :func:`calculate_monthly_payment`,
    :func:`calculate_total_payment`, and :func:`calculate_total_interest`.

    Args:
        principal: Raw loan principal.
        annual_rate: Raw annual interest rate (percent).
        term_value: Raw loan term value.
        term_unit: Raw loan term unit ("months" or "years"), or an
            already-validated TermUnit.

    Returns:
        A fully populated, immutable LoanResult.

    Raises:
        EmptyInputError: If a required field is empty.
        NonNumericInputError: If a numeric field cannot be parsed.
        PrincipalOutOfRangeError: If the principal is out of range.
        InterestRateOutOfRangeError: If the interest rate is out of range.
        InvalidTermValueError: If the term value is not a positive integer.
        InvalidTermUnitError: If the term unit is not recognized.
        TermOutOfRangeError: If the normalized term is out of range.
        CalculationError: If the amortization arithmetic fails
            unexpectedly.
    """
    validated_principal = validate_principal(principal)
    validated_rate = validate_interest_rate(annual_rate)
    validated_term_value = validate_term_value(term_value)
    validated_term_unit = (
        term_unit if isinstance(term_unit, TermUnit) else validate_term_unit(term_unit)
    )
    total_months = normalize_term_to_months(validated_term_value, validated_term_unit)

    monthly_payment = calculate_monthly_payment(validated_principal, validated_rate, total_months)
    total_payment = calculate_total_payment(monthly_payment, total_months)
    total_interest = calculate_total_interest(total_payment, validated_principal)

    return LoanResult(
        principal=validated_principal,
        annual_rate=validated_rate,
        term_months=total_months,
        monthly_payment=monthly_payment,
        total_payment=total_payment,
        total_interest=total_interest,
    )
