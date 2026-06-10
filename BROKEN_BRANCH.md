# The broken-tests exercise: diagnosis & fix walkthrough

This document recreates the exact muscle most live Python screens test: you
inherit a Dockerized repo whose tests are red because of a dependency conflict,
and you have to get `pytest` green inside the container.

There is a branch, `broken-deps`, that ships a deliberately broken
`pyproject.toml`. Below is how I reproduced the failure, diagnosed it from the
traceback, and fixed it. Two independent breaks are walked through — each is a
realistic flavor of the same class of problem.

> TL;DR of the lesson: read the traceback bottom-up, identify which package the
> failing symbol belongs to, then reconcile that package's version with the code
> that uses it (or with its peer packages).

---

## How to reproduce

```bash
git checkout broken-deps
docker build -t ledger-sandbox:broken .
docker run --rm ledger-sandbox:broken    # red
```

(You can also reproduce locally with `pip install ".[dev]" && pytest`.)

---

## Break #1 — Pydantic pinned to v1, code is written for v2

### The broken pin

`broken-deps` changes the Pydantic line in `pyproject.toml` to:

```toml
    "pydantic==1.10.13",
```

### The symptom

The suite never even collects. `docker build` may succeed, but the test run
dies at import time:

```
ImportError while importing test module '/app/tests/test_models.py'.
...
src/ledger/models.py:17: in <module>
    from pydantic import BaseModel, ConfigDict, Field, field_validator
E   ImportError: cannot import name 'field_validator' from 'pydantic'
```

### Diagnosis

Read the bottom line first: `cannot import name 'field_validator'`.
`field_validator` is a **Pydantic v2** symbol — in v1 the decorator was
`@validator`, and `ConfigDict` did not exist either (you used an inner
`class Config`). So the installed Pydantic is older than the code expects.

Confirm what actually resolved inside the container:

```bash
docker run --rm ledger-sandbox:broken pip show pydantic | grep -i version
# Version: 1.10.13
```

That mismatch is the whole bug. The code targets v2; the environment has v1.

### Fix

Restore the v2 pin (and its matching `pydantic-core`, which only exists for v2):

```toml
    "pydantic==2.7.1",
    "pydantic-core==2.18.2",
```

Rebuild and rerun:

```bash
docker build -t ledger-sandbox .
docker run --rm ledger-sandbox     # green
```

### Why not "just fix the code for v1"?

You could rewrite the models for v1, but that's the wrong direction: FastAPI
0.111 itself requires Pydantic v2. Downgrading Pydantic to satisfy one module
would break the framework. The cheapest correct move is to align the pin with
what the rest of the stack already needs.

---

## Break #2 — FastAPI / Starlette / httpx skew

This is the subtler, more interview-realistic version: everything *installs*,
but the API tests explode because the web stack is internally inconsistent.

### The broken pins

```toml
    "fastapi==0.111.0",
    "starlette==0.41.0",   # too new for fastapi 0.111
    "httpx==0.23.0",       # too old for this Starlette TestClient
```

### The symptom

`test_models.py` and `test_core.py` pass, but every test in `test_api.py` fails
at the moment the `TestClient` is constructed:

```
tests/test_api.py:1: in <module>
    from fastapi.testclient import TestClient
...
TypeError: Client.__init__() got an unexpected keyword argument 'app'
```

or, depending on the exact skew:

```
RuntimeError: Starlette 0.41 is not compatible with this version of FastAPI
```

### Diagnosis

The failure is isolated to the API tests, which is the clue: the pure-Python
library tests don't touch the web stack. `TestClient` is a thin wrapper that
Starlette builds on top of **httpx**. Two things have to be true:

1. `fastapi==0.111.0` declares a supported `starlette` range
   (`>=0.37.2,<0.38.0`). `0.41.0` is outside it.
2. Starlette's `TestClient` passes `app=...` into `httpx.Client`, which only
   gained that transport wiring in httpx 0.24+. `httpx==0.23.0` predates it,
   hence the `unexpected keyword argument 'app'`.

Inspect the resolved versions and FastAPI's own requirement:

```bash
docker run --rm ledger-sandbox:broken pip show fastapi | grep -i requires
docker run --rm ledger-sandbox:broken pip index versions starlette
```

### Fix

Pin all three to a mutually compatible set — the one FastAPI 0.111 was released
against:

```toml
    "fastapi==0.111.0",
    "starlette==0.37.2",
    "httpx==0.27.0",
```

Rebuild, rerun, green.

### The general rule

When a single framework (FastAPI) sits on top of peers (Starlette) and a client
(httpx), pin to a **known-good triple** rather than chasing each latest release.
`pip install fastapi==0.111.0` on its own resolves a compatible Starlette; the
trap is overriding one leg of the triple with a "newer is better" pin.

---

## Checklist I run on any red Dockerized repo

1. **Reproduce in the container**, not just locally — the image is the source of
   truth (`docker run --rm <img> pytest -v`).
2. **Read the traceback bottom-up.** The last line names the real error; the
   frames above it tell you which package owns the failing symbol.
3. **Separate collection errors from assertion failures.** An `ImportError`
   during collection is almost always a dependency/version problem, not a logic
   bug.
4. **Ask "which package owns this symbol, and what version introduced/removed
   it?"** (`pip show <pkg>`, `pip index versions <pkg>`).
5. **Reconcile peers as a set**, not one pin at a time, when a framework spans
   multiple packages.
6. **Rebuild from clean** to make sure the fix is the image, not your shell:
   `docker build --no-cache`.
7. **Confirm green inside the container** and capture the output.
