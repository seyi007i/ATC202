"""Tests for the validation and amortization logic in ``module6.calculator``."""

from __future__ import annotations

from decimal import Decimal

import pytest

from module6 import config
from module6.calculator import (
    calculate_loan,
    calculate_monthly_payment,
    calculate_total_interest,
    calculate_total_payment,
    normalize_term_to_months,
    validate_interest_rate,
    validate_principal,
    validate_term_unit,
    validate_term_value,
)
from module6.models import (
    CalculationError,
    EmptyInputError,
    InterestRateOutOfRangeError,
    InvalidTermUnitError,
    InvalidTermValueError,
    NonNumericInputError,
    PrincipalOutOfRangeError,
    TermOutOfRangeError,
    TermUnit,
)


class TestValidatePrincipal:
    """Tests for validate_principal (FR-1, BR-1)."""

    def test_empty_principal_raises_empty_input_error(self) -> None:
        """An empty string must raise EmptyInputError, not crash."""
        with pytest.raises(EmptyInputError):
            validate_principal("")

    def test_whitespace_only_principal_raises_empty_input_error(self) -> None:
        """A whitespace-only string is treated the same as empty."""
        with pytest.raises(EmptyInputError):
            validate_principal("   ")

    def test_non_numeric_principal_raises_non_numeric_input_error(self) -> None:
        """A non-numeric string like "abc" must be rejected clearly."""
        with pytest.raises(NonNumericInputError):
            validate_principal("abc")

    def test_negative_principal_raises_out_of_range_error(self) -> None:
        """A negative principal violates BR-1 (must be positive)."""
        with pytest.raises(PrincipalOutOfRangeError):
            validate_principal("-5000")

    def test_zero_principal_raises_out_of_range_error(self) -> None:
        """Zero is not a valid principal."""
        with pytest.raises(PrincipalOutOfRangeError):
            validate_principal("0")

    def test_principal_above_max_raises_out_of_range_error(self) -> None:
        """A principal above the 100,000,000 cap must be rejected."""
        with pytest.raises(PrincipalOutOfRangeError):
            validate_principal("100000001")

    def test_principal_at_max_boundary_is_valid(self) -> None:
        """Exactly the maximum principal is a valid boundary value."""
        assert validate_principal("100000000") == config.MAX_PRINCIPAL

    def test_accepts_numeric_types_directly(self) -> None:
        """Non-string numeric callers (e.g. int/float) are also accepted."""
        assert validate_principal(10000) == Decimal("10000")

    def test_non_numeric_non_string_type_raises_non_numeric_input_error(self) -> None:
        """A caller passing a non-numeric, non-string type (e.g. a list)
        must be rejected clearly rather than crashing."""
        with pytest.raises(NonNumericInputError):
            validate_principal([1, 2, 3])  # type: ignore[arg-type]


class TestValidateInterestRate:
    """Tests for validate_interest_rate (FR-2, BR-2)."""

    def test_empty_rate_raises_empty_input_error(self) -> None:
        """An empty interest rate must raise EmptyInputError."""
        with pytest.raises(EmptyInputError):
            validate_interest_rate("")

    def test_non_numeric_rate_raises_non_numeric_input_error(self) -> None:
        """A non-numeric string like "five" must be rejected clearly."""
        with pytest.raises(NonNumericInputError):
            validate_interest_rate("five")

    def test_negative_rate_raises_out_of_range_error(self) -> None:
        """A negative interest rate violates BR-2."""
        with pytest.raises(InterestRateOutOfRangeError):
            validate_interest_rate("-2")

    def test_rate_above_100_raises_out_of_range_error(self) -> None:
        """A rate above 100% is outside the allowed range."""
        with pytest.raises(InterestRateOutOfRangeError):
            validate_interest_rate("100.01")

    def test_boundary_rates_0_and_100_are_valid(self) -> None:
        """Both ends of the inclusive [0, 100] range are valid."""
        assert validate_interest_rate("0") == Decimal("0")
        assert validate_interest_rate("100") == Decimal("100")

    def test_decimal_rate_is_valid(self) -> None:
        """Decimal rates like 7.25 must parse correctly (TC-011)."""
        assert validate_interest_rate("7.25") == Decimal("7.25")


class TestValidateTermValue:
    """Tests for validate_term_value (FR-3, BR-3)."""

    def test_empty_term_value_raises_empty_input_error(self) -> None:
        """An empty term value must raise EmptyInputError."""
        with pytest.raises(EmptyInputError):
            validate_term_value("")

    def test_non_numeric_term_value_raises_non_numeric_input_error(self) -> None:
        """A non-numeric term value must be rejected clearly."""
        with pytest.raises(NonNumericInputError):
            validate_term_value("twelve")

    def test_zero_term_value_raises_invalid_term_value_error(self) -> None:
        """Zero is not a valid loan term (BR-3)."""
        with pytest.raises(InvalidTermValueError):
            validate_term_value("0")

    def test_negative_term_value_raises_invalid_term_value_error(self) -> None:
        """A negative term value is invalid."""
        with pytest.raises(InvalidTermValueError):
            validate_term_value("-3")

    def test_non_integer_term_value_raises_invalid_term_value_error(self) -> None:
        """A fractional term value like 12.5 is not a whole number."""
        with pytest.raises(InvalidTermValueError):
            validate_term_value("12.5")

    def test_valid_term_value_returns_int(self) -> None:
        """A valid positive whole number is returned as a plain int."""
        assert validate_term_value("12") == 12


class TestValidateTermUnit:
    """Tests for validate_term_unit (FR-3)."""

    def test_empty_unit_raises_empty_input_error(self) -> None:
        """An empty term unit must raise EmptyInputError."""
        with pytest.raises(EmptyInputError):
            validate_term_unit("")

    def test_invalid_unit_raises_invalid_term_unit_error(self) -> None:
        """A unit that isn't "months"/"years" must be rejected clearly."""
        with pytest.raises(InvalidTermUnitError):
            validate_term_unit("weeks")

    def test_months_and_years_are_valid_case_insensitive(self) -> None:
        """Both units are accepted case-insensitively, with whitespace trimmed."""
        assert validate_term_unit("Months") == TermUnit.MONTHS
        assert validate_term_unit(" YEARS ") == TermUnit.YEARS


class TestNormalizeTermToMonths:
    """Tests for normalize_term_to_months (FR-3, max 25 years)."""

    def test_months_unit_returns_value_unchanged(self) -> None:
        """A term already in months is passed through unchanged."""
        assert normalize_term_to_months(24, TermUnit.MONTHS) == 24

    def test_years_unit_converts_to_months(self) -> None:
        """A term in years is converted to months (x12)."""
        assert normalize_term_to_months(2, TermUnit.YEARS) == 24

    def test_term_at_300_months_boundary_is_valid(self) -> None:
        """Exactly 300 months (25 years) is the valid maximum boundary."""
        assert normalize_term_to_months(300, TermUnit.MONTHS) == 300
        assert normalize_term_to_months(25, TermUnit.YEARS) == 300

    def test_term_above_300_months_raises_term_out_of_range_error(self) -> None:
        """One month past the 25-year cap must be rejected (TC-013, adjusted
        from the spec's inconsistent 40-year test case to the authoritative
        25-year/300-month cap in FR-3)."""
        with pytest.raises(TermOutOfRangeError):
            normalize_term_to_months(301, TermUnit.MONTHS)

    def test_term_below_min_raises_term_out_of_range_error(self) -> None:
        """A term of 0 months is below the 1-month minimum."""
        with pytest.raises(TermOutOfRangeError):
            normalize_term_to_months(0, TermUnit.MONTHS)


class TestCalculateMonthlyPayment:
    """Tests for calculate_monthly_payment (FR-4, BR-4)."""

    def test_standard_amortization_matches_known_value(self) -> None:
        """TC-001: $100,000 at 5% for 20 years (240 months, within the
        25-year cap) matches the standard amortization formula: $659.96/month."""
        payment = calculate_monthly_payment(Decimal("100000"), Decimal("5"), 240)
        assert payment == Decimal("659.96")

    def test_zero_interest_rate_uses_simple_division(self) -> None:
        """TC-002: 0% interest falls back to Principal / Number of Months
        (BR-4): $12,000 over 12 months is exactly $1,000.00/month."""
        payment = calculate_monthly_payment(Decimal("12000"), Decimal("0"), 12)
        assert payment == Decimal("1000.00")

    def test_decimal_interest_rate_matches_known_value(self) -> None:
        """TC-011: a decimal rate of 7.25% must calculate correctly."""
        payment = calculate_monthly_payment(Decimal("50000"), Decimal("7.25"), 60)
        assert payment == Decimal("995.97")

    def test_zero_total_months_raises_calculation_error(self) -> None:
        """A total_months of 0 would divide by zero; this must surface as a
        CalculationError rather than an unhandled ZeroDivisionError."""
        with pytest.raises(CalculationError):
            calculate_monthly_payment(Decimal("1000"), Decimal("0"), 0)


class TestCalculateTotalPayment:
    """Tests for calculate_total_payment (FR-5)."""

    def test_total_payment_equals_monthly_times_months(self) -> None:
        """Total payment is monthly payment multiplied by the term."""
        total = calculate_total_payment(Decimal("659.96"), 240)
        assert total == Decimal("158390.40")


class TestCalculateTotalInterest:
    """Tests for calculate_total_interest (FR-6)."""

    def test_total_interest_equals_total_payment_minus_principal(self) -> None:
        """Total interest is total payment minus the original principal."""
        interest = calculate_total_interest(Decimal("158390.40"), Decimal("100000"))
        assert interest == Decimal("58390.40")

    def test_zero_interest_loan_has_zero_total_interest(self) -> None:
        """TC-002: a zero-rate loan has exactly zero total interest."""
        interest = calculate_total_interest(Decimal("12000.00"), Decimal("12000"))
        assert interest == Decimal("0.00")


class TestCalculateLoan:
    """End-to-end tests for the calculate_loan orchestrator."""

    def test_returns_full_result_with_correct_totals(self) -> None:
        """TC-001/TC-003: a standard valid loan produces correct monthly
        payment, total payment, and total interest."""
        result = calculate_loan("100000", "5", "20", "years")
        assert result.term_months == 240
        assert result.monthly_payment == Decimal("659.96")
        assert result.total_payment == Decimal("158390.40")
        assert result.total_interest == Decimal("58390.40")

    def test_zero_interest_full_result(self) -> None:
        """TC-002: end-to-end zero-interest calculation."""
        result = calculate_loan("12000", "0", "12", "months")
        assert result.monthly_payment == Decimal("1000.00")
        assert result.total_payment == Decimal("12000.00")
        assert result.total_interest == Decimal("0.00")

    def test_large_principal_within_limit_calculates_correctly(self) -> None:
        """TC-012: the maximum allowed principal (100,000,000) must
        calculate correctly and quickly."""
        result = calculate_loan("100000000", "5", "240", "months")
        assert result.monthly_payment == Decimal("659955.74")

    def test_max_term_300_months_boundary_is_valid(self) -> None:
        """TC-013 (adjusted to the 25-year/300-month cap): the maximum term
        is accepted."""
        result = calculate_loan("10000", "6", "25", "years")
        assert result.term_months == 300
        assert result.monthly_payment == Decimal("64.43")

    def test_term_over_max_raises_term_out_of_range_error(self) -> None:
        """TC-013 (adjusted): a term exceeding 25 years must be rejected."""
        with pytest.raises(TermOutOfRangeError):
            calculate_loan("10000", "6", "301", "months")

    def test_accepts_pre_validated_term_unit_enum(self) -> None:
        """Programmatic callers may pass an already-validated TermUnit."""
        result = calculate_loan("12000", "0", "12", TermUnit.MONTHS)
        assert result.monthly_payment == Decimal("1000.00")

    def test_empty_principal_raises_empty_input_error(self) -> None:
        """TC-004: an empty loan amount must produce a validation error."""
        with pytest.raises(EmptyInputError):
            calculate_loan("", "5", "12", "months")

    def test_empty_interest_rate_raises_empty_input_error(self) -> None:
        """TC-005: an empty interest rate must produce a validation error."""
        with pytest.raises(EmptyInputError):
            calculate_loan("1000", "", "12", "months")

    def test_empty_term_raises_empty_input_error(self) -> None:
        """TC-006: an empty loan term must produce a validation error."""
        with pytest.raises(EmptyInputError):
            calculate_loan("1000", "5", "", "months")

    def test_100_consecutive_calculations_are_consistent(self) -> None:
        """TC-015: 100 consecutive calculations with the same inputs must
        produce identical, accurate results with no errors."""
        results = [calculate_loan("100000", "5", "20", "years") for _ in range(100)]
        assert all(result.monthly_payment == Decimal("659.96") for result in results)
        assert all(result.total_interest == Decimal("58390.40") for result in results)
