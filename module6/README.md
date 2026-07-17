# Simple Loan Calculator

A stdlib-only Python CLI that computes the monthly payment, total
repayment amount, and total interest for a fixed-rate, fully amortizing
loan. Built to the accompanying engineering specification, with all
monetary output rounded to exactly 2 decimal places.

## Project Overview

The calculator collects a loan principal, an annual interest rate, and a
loan term (in months or years), validates each field with a descriptive
error message on failure, and computes:

| Output           | Formula                                                          |
| ----------------- | ----------------------------------------------------------------- |
| Monthly payment    | `P * r * (1+r)^n / ((1+r)^n - 1)`, or `P / n` when rate is 0%    |
| Total payment      | `Monthly payment * n`                                            |
| Total interest      | `Total payment - Principal`                                      |

where `P` is the principal, `r` is the monthly interest rate
(`annual_rate / 100 / 12`), and `n` is the total number of monthly
payments.

**Note on the loan-term limit**: the engineering spec's FR-3 caps the
loan term at 25 years (300 months); this is the enforced maximum. An
earlier draft test case referenced a 40-year maximum — that has been
superseded by the 300-month/25-year boundary used throughout this
implementation and its tests.

## Architecture

```
module6/
│
├── calculator.py   # Pure validation + amortization math, no I/O
├── session.py       # LoanCalculatorSession: CLI state + reset() (FR-8)
├── cli.py            # Interactive calculate/reset/exit menu loop
├── models.py          # LoanResult, TermUnit, and the exception hierarchy
├── config.py           # Numeric limits (BR-1..BR-5) and rounding rule
├── __main__.py           # `python -m module6` entry point
├── tests/
│   ├── test_calculator.py  # Validation boundaries + amortization math
│   ├── test_session.py      # Reset/state behavior
│   └── test_cli.py            # Full interactive-loop behavior
├── requirements.txt
└── README.md
```

**Design notes**

- **Models**: `LoanResult` is an immutable `@dataclass`, and every
  validation failure has its own named exception rooted in one base,
  `LoanCalculatorError` (`ValidationError` → `EmptyInputError`,
  `NonNumericInputError`, `PrincipalOutOfRangeError`,
  `InterestRateOutOfRangeError`, `InvalidTermValueError`,
  `InvalidTermUnitError`, `TermOutOfRangeError`; and `CalculationError`
  for unexpected arithmetic failures).
- **Rounding**: all monetary values are rounded using `decimal.Decimal`
  with `ROUND_HALF_UP` (BR-5), not naive `round()` on floats, to avoid
  float-imprecision and banker's-rounding artifacts in currency output.
- **Separation of concerns**: `calculator.py` has zero I/O and is fully
  unit-testable by passing plain values; `session.py` holds CLI state
  (including the FR-8 "Reset" behavior) with no coupling to
  stdin/stdout; `cli.py` is the only module that calls `input()`/`print()`,
  and both are parameterized (`input_func`/`print_func`) so `test_cli.py`
  can drive the loop with fake callables.
- **Error handling**: The CLI catches every `LoanCalculatorError`
  subclass and prints a clear, descriptive message — it never crashes on
  invalid input.

## Installation

Requires Python 3.12+.

```bash
cd module6
pip install -r requirements.txt
```

No external services or dependencies are required — the application
itself uses only the Python standard library (`pytest`/`pytest-cov` are
only needed to run the test suite).

## Dependencies

- [`pytest`](https://pytest.org) — test runner
- [`pytest-cov`](https://pytest-cov.readthedocs.io) — coverage reporting

## How to Run

```bash
python -m module6
```

This starts the interactive menu:

```
Simple Loan Calculator
  [C]alculate
  [R]eset
  [E]xit
Choose an option:
```

## How to Run Tests

From the directory **containing** `module6/` (i.e. one level above it):

```bash
pytest module6/tests -v
```

With coverage:

```bash
pytest module6/tests --cov=module6 --cov-report=term-missing
```

## Example API Usage

```python
from module6 import calculate_loan

result = calculate_loan(
    principal="100000",
    annual_rate="5",
    term_value="240",
    term_unit="months",
)
print(result.monthly_payment)   # Decimal('659.96')
print(result.total_payment)     # Decimal('158390.40')
print(result.total_interest)    # Decimal('58390.40')
```

Zero-interest loans use simple division (BR-4):

```python
result = calculate_loan("12000", "0", "12", "months")
print(result.monthly_payment)   # Decimal('1000.00')
print(result.total_interest)    # Decimal('0.00')
```

## Sample Session

```
Simple Loan Calculator
  [C]alculate
  [R]eset
  [E]xit
Choose an option: c
Loan principal: 100000
Annual interest rate (%): 5
Loan term (number): 20
Loan term unit (months/years): years

Results
  Monthly payment: 659.96
  Total payment:   158390.40
  Total interest:  58390.40

Simple Loan Calculator
  [C]alculate
  [R]eset
  [E]xit
Choose an option: r
Calculator has been reset.

Simple Loan Calculator
  [C]alculate
  [R]eset
  [E]xit
Choose an option: e
Goodbye.
```

**Error handling — invalid input**

```
Choose an option: c
Loan principal: abc
Annual interest rate (%): 5
Loan term (number): 12
Loan term unit (months/years): months
Error: Loan principal must be a valid number, got 'abc'.
```
