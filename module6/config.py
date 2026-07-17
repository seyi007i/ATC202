"""Centralized, configurable constants for the Simple Loan Calculator.

Keeping numeric limits and rounding rules in one module makes the
business rules (FR-1..FR-3, BR-1..BR-5) adjustable without touching
validation or calculation logic elsewhere.
"""

from __future__ import annotations

from decimal import Decimal

#: Maximum allowed loan principal (FR-1).
MAX_PRINCIPAL: Decimal = Decimal("100000000")

#: Minimum allowed annual interest rate, percent (FR-2).
MIN_INTEREST_RATE: Decimal = Decimal("0")

#: Maximum allowed annual interest rate, percent (FR-2).
MAX_INTEREST_RATE: Decimal = Decimal("100")

#: Number of months in a year, used to convert year-denominated terms.
MONTHS_PER_YEAR: int = 12

#: Minimum allowed total loan term, in months (FR-3).
MIN_TERM_MONTHS: int = 1

#: Maximum allowed total loan term, in months: 25 years (FR-3).
MAX_TERM_MONTHS: int = 25 * MONTHS_PER_YEAR

#: Quantization target for all monetary outputs: 2 decimal places (BR-5).
CURRENCY_QUANTIZE: Decimal = Decimal("0.01")
