"""ledger - a small budgeting ledger library and API.

Public surface:
    Transaction        - a single validated money movement
    Ledger             - an in-memory collection with balance/summary logic
    Category           - allowed spending categories
"""

from ledger.models import Category, Transaction
from ledger.core import Ledger

__all__ = ["Category", "Transaction", "Ledger"]
__version__ = "0.1.0"
