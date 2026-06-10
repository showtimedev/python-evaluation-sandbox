# The broken-tests exercise: diagnosis & fix walkthrough

This document recreates the exact muscle most live Python screens test: you
inherit a Dockerized repo whose tests are red because of a dependency conflict,
and you have to get `pytest` green inside the container.

There is a branch, `broken-deps`, that ships a deliberately broken
`pyproject.toml`. Below is how I reproduced the failure, diagnosed it from the
traceback, and fixed it.

> Every command output quoted below was captured from an actual run on this
> machine (macOS, Python 3.11 host; the container runs Python 3.12.4). Nothing
> here is illustrative-only; where a second scenario behaves differently from
> what you might expect, that's called out explicitly.

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

## The break on `broken-deps` — Pydantic pinned to v1, code is written for v2

### The broken pin

`broken-deps` changes the Pydantic line in `pyproject.toml` to:

```toml
    "pydantic==1.10.13",
```

and drops the `pydantic-core` pin (pydantic-core is a v2-only package).

This combination *installs cleanly*. FastAPI 0.111 declares
`pydantic>=1.7.4,<3.0.0` (verified below), so pip is happy to resolve Pydantic
v1 alongside it. The failure surfaces only when our code imports a v2 symbol.

### The symptom

The suite never even collects. The test run dies at import time:

```
ImportError while importing test module '/app/tests/test_models.py'.
...
src/ledger/models.py:16: in <module>
    from pydantic import BaseModel, ConfigDict, Field, field_validator
E   ImportError: cannot import name 'field_validator' from 'pydantic'
```

pytest reports `3 errors during collection` (one per test module, since all
three import the library).

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
docker run --rm ledger-sandbox     # green: 15 passed
```

### Why not "just fix the code for v1"?

You could rewrite the models for v1, but that's the wrong direction. The rest of
the codebase (and the FastAPI request/response models) is written against the v2
API, so the cheapest correct move is to align the pin with what the code already
uses rather than rewriting working code to satisfy a downgraded dependency.

Note: FastAPI 0.111 does **not** force this for you — it accepts Pydantic v1 or
v2. Verified requirement:

```bash
python -c "import importlib.metadata as m; print([r for r in m.requires('fastapi') if 'pydantic' in r or 'starlette' in r])"
# ['starlette<0.38.0,>=0.37.2',
#  'pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4', ...]
```

That `>=1.7.4` is exactly why the broken pin installed without complaint and
failed later, at import — the more interesting failure mode to practice.

---

## A second scenario worth knowing: peer-version skew (install-time conflict)

The pinned set in `pyproject.toml` (`fastapi==0.111.0`, `starlette==0.37.2`,
`httpx==0.27.0`) is a mutually compatible triple. A natural question is "what
happens if I bump just one of them?" I tried it so the answer here is measured,
not guessed.

I attempted to install an inconsistent set in a throwaway venv:

```bash
pip install "fastapi==0.111.0" "starlette==0.41.0" "httpx==0.23.0"
```

With a modern pip resolver this does **not** get far enough to produce a runtime
traceback — it fails at dependency resolution. Actual captured output:

```
ERROR: Cannot install fastapi==0.111.0 and starlette==0.41.0 because these
package versions have conflicting dependencies.

The conflict is caused by:
    The user requested starlette==0.41.0
    fastapi 0.111.0 depends on starlette<0.38.0 and >=0.37.2

ERROR: ResolutionImpossible
```

### Why this matters for the diagnosis

This is the *good* failure mode: the resolver catches the skew before anything
runs. The lesson is the inverse of the Pydantic case — there, a too-loose
upstream constraint (`pydantic>=1.7.4`) let an incompatible version through to
fail at import; here, FastAPI's tight `starlette<0.38.0` constraint stops the
bad combination at install time.

The general rule that covers both: when a framework (FastAPI) sits on top of a
peer (Starlette) and a client (httpx), pin to a **known-good set** and let the
framework's own constraints validate it, rather than overriding one leg with a
"newer is better" pin.

---

## Checklist I run on any red Dockerized repo

1. **Reproduce in the container**, not just locally — the image is the source of
   truth (`docker run --rm <img> pytest -v`).
2. **Read the traceback bottom-up.** The last line names the real error; the
   frames above it tell you which package owns the failing symbol.
3. **Separate collection errors from assertion failures.** An `ImportError`
   during collection is almost always a dependency/version problem, not a logic
   bug.
4. **Separate install-time conflicts from runtime errors.** A
   `ResolutionImpossible` means pip caught the skew up front; an `ImportError`
   or `TypeError` at runtime means a too-loose constraint let a bad version
   through.
5. **Ask "which package owns this symbol, and what version introduced/removed
   it?"** (`pip show <pkg>`, `pip index versions <pkg>`).
6. **Rebuild from clean** to make sure the fix is the image, not your shell:
   `docker build --no-cache`.
7. **Confirm green inside the container** and capture the output.
