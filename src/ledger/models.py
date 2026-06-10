"""Domain models for the ledger, built on Pydantic v2.

These deliberately use Pydantic v2-only APIs (``field_validator``,
``model_config``, ``model_dump``). If the environment resolves Pydantic v1,
imports here fail loudly - which is exactly the kind of dependency drift the
sandbox is meant to rehearse.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from enum import Enum

from dateutil.parser import isoparse
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(str, Enum):
    """Allowed transaction categories."""

    INCOME = "income"
    GROCERIES = "groceries"
    RENT = "rent"
    UTILITIES = "utilities"
    ENTERTAINMENT = "entertainment"
    TRANSFER = "transfer"
    OTHER = "other"


class Transaction(BaseModel):
    """A single validated money movement.

    Positive ``amount`` is money in, negative is money out. Amounts are stored
    as :class:`~decimal.Decimal` to avoid float rounding error on money.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., min_length=1)
    amount: Decimal
    category: Category
    description: str = Field(default="", max_length=280)
    occurred_at: date

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_amount(cls, value: object) -> Decimal:
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError(f"invalid amount: {value!r}") from exc

    @field_validator("amount")
    @classmethod
    def _non_zero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("amount must be non-zero")
        return value

    @field_validator("occurred_at", mode="before")
    @classmethod
    def _parse_date(cls, value: object) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return isoparse(value).date()
        raise ValueError(f"unsupported date value: {value!r}")

    @property
    def is_credit(self) -> bool:
        """True when this transaction adds money to the ledger."""
        return self.amount > 0
