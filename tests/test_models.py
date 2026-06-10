from decimal import Decimal
from datetime import date

import pytest
from pydantic import ValidationError

from ledger.models import Category, Transaction


def test_transaction_coerces_amount_to_decimal():
    txn = Transaction(
        id="t1",
        amount="12.34",
        category=Category.GROCERIES,
        occurred_at="2024-01-05",
    )
    assert txn.amount == Decimal("12.34")
    assert isinstance(txn.amount, Decimal)


def test_transaction_parses_iso_date():
    txn = Transaction(
        id="t2",
        amount=Decimal("-5"),
        category=Category.OTHER,
        occurred_at="2024-03-09T13:45:00Z",
    )
    assert txn.occurred_at == date(2024, 3, 9)


def test_zero_amount_rejected():
    with pytest.raises(ValidationError):
        Transaction(
            id="t3",
            amount=0,
            category=Category.OTHER,
            occurred_at="2024-01-01",
        )


def test_extra_fields_forbidden():
    with pytest.raises(ValidationError):
        Transaction(
            id="t4",
            amount=10,
            category=Category.INCOME,
            occurred_at="2024-01-01",
            unexpected="nope",
        )


def test_is_credit():
    credit = Transaction(id="c", amount=10, category=Category.INCOME, occurred_at="2024-01-01")
    debit = Transaction(id="d", amount=-10, category=Category.RENT, occurred_at="2024-01-01")
    assert credit.is_credit is True
    assert debit.is_credit is False


def test_transaction_is_frozen():
    txn = Transaction(id="f", amount=1, category=Category.OTHER, occurred_at="2024-01-01")
    with pytest.raises(ValidationError):
        txn.amount = Decimal("2")
