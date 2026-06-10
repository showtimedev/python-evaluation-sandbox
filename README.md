# python-evaluation-sandbox

A small, runnable Python project that lives inside Docker. It contains a
budgeting ledger library, a minimal FastAPI service, and a pytest suite that
runs green inside the container. A second branch ships a deliberately broken
dependency pin so the diagnose-and-fix workflow can be practiced end to end.

## Problem

Live Python engineering screens often hand you a Dockerfile and a repo whose
tests are red because of a dependency conflict. You have to get pytest green
inside an isolated environment, usually while screen-sharing. This repo is a
rehearsal of that exact task. It holds a known-good baseline on `main` and a
broken state on `broken-deps`, with a written walkthrough of how the break was
diagnosed and fixed.

## Stack

- Python 3.11+ (the container runs 3.12.4).
- FastAPI + Starlette for the HTTP service.
- Pydantic v2 for validation.
- pytest + pytest-cov for tests.
- Docker for the isolated, reproducible environment.

All dependencies are pinned to exact versions in `pyproject.toml`.

## Architecture

```
                 docker build
                      |
                      v
        +-----------------------------+
        |   python:3.12.4-slim image  |
        |                             |
        |   /opt/venv  (isolated)     |
        |     |                       |
        |     |  pip install .[dev]   |
        |     v                       |
        |   src/ledger/               |
        |     models.py  (Pydantic)   |
        |     core.py    (Ledger)     |
        |     api.py     (FastAPI)    |
        |        ^                    |
        |        | imports            |
        |   tests/  --> pytest        |  <-- CMD on container start
        +-----------------------------+
                      |
                      v
              15 tests, green
```

Request path through the service:

```
client --> POST /transactions --> TransactionIn (Pydantic)
                                      |
                                      v
                             Transaction.model_validate
                                      |
                                      v
                              Ledger.add (in-memory)
       client <-- GET /summary <-- SummaryOut (count/balance/income/spending)
```

## Quick Start

Run with Docker (recommended):

```bash
docker build -t ledger-sandbox .
docker run --rm ledger-sandbox                 # runs pytest, the default command
docker run --rm ledger-sandbox pytest -v       # verbose
docker run --rm ledger-sandbox pytest --cov=ledger --cov-report=term-missing
```

Run locally without Docker:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install ".[dev]"
pytest -v
```

Run the API:

```bash
docker run --rm -p 8000:8000 ledger-sandbox ledger-serve
curl localhost:8000/health
curl -X POST localhost:8000/transactions \
  -H 'content-type: application/json' \
  -d '{"id":"a","amount":"1000.00","category":"income","occurred_at":"2024-01-01"}'
curl localhost:8000/summary
```

Run the broken-tests exercise:

```bash
git checkout broken-deps
docker build -t ledger-sandbox:broken .
docker run --rm ledger-sandbox:broken          # tests fail at collection
```

See [`BROKEN_BRANCH.md`](./BROKEN_BRANCH.md) for the diagnosis and fix.

<!-- SCREENSHOT: terminal showing `docker run --rm ledger-sandbox pytest -v` with all 15 tests passing -->
![all tests passing](docs/screenshots/tests-passing.png)

## Design Decisions

- Money is stored as `Decimal`, not `float`, so summing transactions does not
  accumulate binary rounding error.
- The library uses Pydantic v2-only APIs (`field_validator`, `ConfigDict`,
  `model_dump`, `model_validate`). This is deliberate: it makes the v1-vs-v2
  break on `broken-deps` fail loudly at import, which is the point of the
  exercise.
- The API is exercised through Starlette's `TestClient`, which imports httpx.
  That ties three packages together (fastapi, starlette, httpx), so they are
  pinned as a known-good set rather than to "latest".
- The Dockerfile installs into an isolated `/opt/venv` and never touches the
  system interpreter, so the build is reproducible and the test run is the
  source of truth.
- `create_app()` is an application factory so each test gets a fresh in-memory
  ledger with no shared state.

## Known Limitations & Failure Modes

- Storage is in-memory only. Restarting the service drops all transactions.
  There is no database.
- The API has no authentication or authorization. Do not expose it to a network
  without adding access control. It is meant to run locally or in CI.
- Validation errors are returned as plain strings in the `detail` field rather
  than a structured error schema.
- The `broken-deps` Pydantic v1 pin installs cleanly and only fails at import,
  because FastAPI 0.111 accepts `pydantic>=1.7.4`. The failure is intentional;
  see the walkthrough.
- Sample/test data is synthetic. See the note below.

## What I'd Build Next

- Add a persistence layer (SQLite via SQLAlchemy) behind the same `Ledger`
  interface, so the in-memory store becomes one implementation among several.
- Add a GitHub Actions workflow that builds the image and runs the suite on
  every push, so green-in-container is enforced in CI.
- Add structured error responses and request-id logging to the service.
- Add a second documented break (peer-version skew) on its own branch, captured
  from a real failing run.

## Synthetic Data Note

This project contains no real customer, financial, or personal data. The values
used in the tests (transaction ids, amounts, categories, dates) are synthetic
and exist only to exercise the code. Do not treat them as real records.

## License

MIT. See [LICENSE](./LICENSE).
