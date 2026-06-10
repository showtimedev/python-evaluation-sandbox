"""A small FastAPI service exposing the ledger.

Kept intentionally minimal but real: it imports FastAPI, builds a router, and
relies on Pydantic v2 request/response models. The test suite exercises it
through Starlette's TestClient (which needs httpx), so the FastAPI / Starlette
/ httpx versions must agree.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError

from ledger.core import DuplicateTransactionError, Ledger
from ledger.models import Category, Transaction


class TransactionIn(BaseModel):
    id: str
    amount: Decimal
    category: Category
    description: str = ""
    occurred_at: str


class SummaryOut(BaseModel):
    count: int
    balance: Decimal
    income: Decimal
    spending: Decimal


def create_app() -> FastAPI:
    """Application factory so tests get a fresh ledger each time."""
    app = FastAPI(title="Ledger Sandbox", version="0.1.0")
    ledger = Ledger()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/transactions", status_code=201)
    def add_transaction(payload: TransactionIn) -> dict[str, str]:
        try:
            txn = Transaction.model_validate(payload.model_dump())
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            ledger.add(txn)
        except DuplicateTransactionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"id": txn.id}

    @app.get("/summary", response_model=SummaryOut)
    def summary() -> SummaryOut:
        return SummaryOut(
            count=len(ledger),
            balance=ledger.balance,
            income=ledger.income(),
            spending=ledger.spending(),
        )

    return app


app = create_app()


def run() -> None:  # pragma: no cover - entrypoint
    import uvicorn

    uvicorn.run("ledger.api:app", host="127.0.0.1", port=8000, reload=False)
