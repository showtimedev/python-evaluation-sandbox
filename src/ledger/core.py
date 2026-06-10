"""Core ledger logic: holding transactions and computing summaries."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from datetime import date
from typing import Iterable

from ledger.models import Category, Transaction


class DuplicateTransactionError(ValueError):
    """Raised when a transaction id is added twice."""


class Ledger:
    """An in-memory collection of transactions with summary helpers."""

    def __init__(self, transactions: Iterable[Transaction] | None = None) -> None:
        self._by_id: dict[str, Transaction] = {}
        for txn in transactions or ():
            self.add(txn)

    def add(self, txn: Transaction) -> None:
        """Add a transaction. Raises on duplicate id."""
        if txn.id in self._by_id:
            raise DuplicateTransactionError(f"duplicate transaction id: {txn.id}")
        self._by_id[txn.id] = txn

    def __len__(self) -> int:
        return len(self._by_id)

    def __iter__(self):
        return iter(self._by_id.values())

    @property
    def balance(self) -> Decimal:
        """Net balance across all transactions."""
        return sum((t.amount for t in self._by_id.values()), Decimal("0"))

    def totals_by_category(self) -> dict[Category, Decimal]:
        """Sum of amounts grouped by category, only for categories present."""
        totals: dict[Category, Decimal] = defaultdict(lambda: Decimal("0"))
        for txn in self._by_id.values():
            totals[txn.category] += txn.amount
        return dict(totals)

    def spending(self) -> Decimal:
        """Total money out (returned as a positive number)."""
        out = sum(
            (t.amount for t in self._by_id.values() if not t.is_credit),
            Decimal("0"),
        )
        return -out

    def income(self) -> Decimal:
        """Total money in."""
        return sum(
            (t.amount for t in self._by_id.values() if t.is_credit),
            Decimal("0"),
        )

    def between(self, start: date, end: date) -> "Ledger":
        """Return a new ledger with transactions in [start, end] inclusive."""
        if start > end:
            raise ValueError("start must be <= end")
        selected = [
            t for t in self._by_id.values() if start <= t.occurred_at <= end
        ]
        return Ledger(selected)
