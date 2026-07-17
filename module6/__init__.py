"""Simple Loan Calculator: a stdlib-only CLI for amortized loan payments.

Exposes the primary calculation entry point,
:func:`~module6.calculator.calculate_loan`, and its result type,
:class:`~module6.models.LoanResult`, for convenient top-level imports.
"""

from __future__ import annotations

from module6.calculator import calculate_loan
from module6.models import LoanResult

__version__ = "1.0.0"

__all__ = ["calculate_loan", "LoanResult"]
