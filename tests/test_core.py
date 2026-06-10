from decimal import Decimal
from datetime import date

import pytest

from ledger.core import DuplicateTransactionError, Ledger
from ledger.models import Category, Transaction


def _txn(id, amount, category=Category.OTHER, day="2024-01-01"):
    return Transaction(id=id, amount=amount, category=category, occurred_at=day)


def test_balance_income_and_spending():
    led = Ledger(
        [
            _txn("a", "1000.00", Category.INCOME),
            _txn("b", "-250.50", Category.RENT),
            _txn("c", "-49.50", Category.GROCERIES),
        ]
    )
    assert led.balance == Decimal("700.00")
    assert led.income() == Decimal("1000.00")
    assert led.spending() == Decimal("300.00")
    assert len(led) == 3


def test_duplicate_id_rejected():
    led = Ledger([_txn("dup", 10)])
    with pytest.raises(DuplicateTransactionError):
        led.add(_txn("dup", 20))


def test_totals_by_category():
    led = Ledger(
        [
            _txn("a", "-10", Category.GROCERIES),
            _txn("b", "-15", Category.GROCERIES),
            _txn("c", "2000", Category.INCOME),
        ]
    )
    totals = led.totals_by_category()
    assert totals[Category.GROCERIES] == Decimal("-25")
    assert totals[Category.INCOME] == Decimal("2000")


def test_between_filters_inclusive():
    led = Ledger(
        [
            _txn("jan", "10", day="2024-01-15"),
            _txn("feb", "20", day="2024-02-15"),
            _txn("mar", "30", day="2024-03-15"),
        ]
    )
    window = led.between(date(2024, 1, 31), date(2024, 2, 28))
    ids = {t.id for t in window}
    assert ids == {"feb"}


def test_between_bad_range():
    led = Ledger()
    with pytest.raises(ValueError):
        led.between(date(2024, 2, 1), date(2024, 1, 1))
