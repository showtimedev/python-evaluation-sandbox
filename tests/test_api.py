from fastapi.testclient import TestClient

from ledger.api import create_app


def client():
    return TestClient(create_app())


def test_health():
    resp = client().get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_post_transaction_and_summary():
    c = client()
    r1 = c.post(
        "/transactions",
        json={
            "id": "a",
            "amount": "1000.00",
            "category": "income",
            "occurred_at": "2024-01-01",
        },
    )
    assert r1.status_code == 201

    r2 = c.post(
        "/transactions",
        json={
            "id": "b",
            "amount": "-300.00",
            "category": "rent",
            "occurred_at": "2024-01-02",
        },
    )
    assert r2.status_code == 201

    summary = c.get("/summary").json()
    assert summary["count"] == 2
    assert summary["balance"] == "700.00"
    assert summary["income"] == "1000.00"
    assert summary["spending"] == "300.00"


def test_duplicate_returns_409():
    c = client()
    payload = {
        "id": "dup",
        "amount": "5",
        "category": "other",
        "occurred_at": "2024-01-01",
    }
    assert c.post("/transactions", json=payload).status_code == 201
    assert c.post("/transactions", json=payload).status_code == 409


def test_zero_amount_rejected_422():
    c = client()
    resp = c.post(
        "/transactions",
        json={"id": "z", "amount": "0", "category": "other", "occurred_at": "2024-01-01"},
    )
    assert resp.status_code == 422
