---
name: python-coding
description: >
  Sets up and maintains Python projects using uv, ruff, ty, strict typing, FastAPI, Strawberry,
  SQLAlchemy, Alembic, Pydantic, dataclasses, semver, and structured JSON (wide-event) logging.
  Use when creating a Python app or library, scaffolding services (REST, GraphQL, daemon),
  choosing project layout, or when the user asks for Python best practices aligned with this stack.
---

# Python coding

## When this skill applies

Use this skill for **new Python projects** and **ongoing development** where the stack below is appropriate. Combine with tests using the **using-pytest** skill: follow [using-pytest/SKILL.md](../using-pytest/SKILL.md) for Given/When/Then/Clean, plain test functions, and layer organization.

---

## Canonical project layout

### Application / service

```
my-service/
├── pyproject.toml
├── .python-version
├── uv.lock
├── src/
│   └── my_service/
│       ├── __init__.py
│       ├── main.py          # entrypoint / app factory
│       ├── settings.py      # BaseSettings + module constants (Final / UPPER_SNAKE)
│       ├── models/          # SQLAlchemy ORM models
│       ├── schemas/         # Pydantic request/response schemas
│       ├── routers/         # FastAPI routers or Strawberry resolvers
│       └── services/        # business logic (no HTTP / ORM imports)
└── tests/
```

### Library

```
my-lib/
├── pyproject.toml
├── .python-version
├── uv.lock
├── src/
│   └── my_lib/
│       ├── __init__.py      # expose public API; set __all__
│       └── py.typed         # PEP 561 marker
└── tests/
```

---

## Runtime and environment

- **Never rely on the system Python.** Always use the virtual environment created and managed by **uv** (`uv venv`, `uv sync`, `uv run`).
- Pin a **single Python version** for the project (e.g. in `.python-version` and/or `pyproject.toml`) and document it for CI and contributors.

---

## Package and tool management (uv)

- Use **uv** for dependency resolution, lockfiles, and running commands (`uv add`, `uv remove`, `uv run <command>`).
- Prefer `pyproject.toml` as the source of truth for project metadata and dependencies.
- Expose common tasks via **scripts** or documented `uv run` invocations (lint, typecheck, test).

---

## Linting and formatting (ruff)

- Use **ruff** for linting and formatting with commonly adopted defaults, for example:
  - Enable rule sets such as **E, W, F, I, UP, B, SIM** (adjust to project needs).
  - Line length **88** (Black-compatible) unless the project already standardizes another value.
  - `ruff format` for formatting; `ruff check` for lint (with `--fix` in dev loops).
- Keep ruff configuration in `pyproject.toml` under `[tool.ruff]` and `[tool.ruff.lint]`.

---

## Static typing (always) and type checking (ty)

- **Always use typing**: annotate function signatures, public APIs, and non-obvious variables; prefer modern syntax (`list[str]`, `dict[str, Any]` with care, `X | Y` unions on supported Python versions).
- Prefer `**from __future__ import annotations`** when it simplifies forward references and reduces quote noise (project-wide consistency).
- **Import for typing under `TYPE_CHECKING`** when it avoids runtime import cycles or heavy optional dependencies:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from myapp.db import Session

def use_session(session: Session) -> None:
    ...
```

- Use **ty** (Astral's Rust-based type checker, shipped alongside ruff) for static type checking; run it in CI alongside ruff. If `ty` is unavailable or blocked, use `**mypy`** with `strict = true` as the fallback. Either way, type checking must run in CI and block merges on errors.

---

## Settings and configuration

Use a single `**settings.py**` at the package root for:

1. **Runtime settings** — env-backed values via `**pydantic-settings`** (`BaseSettings`).
2. **Constants** — static, non-secret values that do not belong in the environment (defaults shared across modules, protocol limits, feature toggles fixed in code).

### Runtime settings (`BaseSettings`)

- Read values from **environment variables** or `.env` files; never hard-code secrets.
- Validate and document every setting at the module boundary — fail fast on startup if required values are missing.

### Constants (same module)

- Define **module-level constants** with `**typing.Final`**, `**UPPER_SNAKE_CASE**`, and explicit types.
- Prefer `**frozenset**` / tuples for immutable collections; avoid mutable defaults at import time.
- Keep constants **small and stable**; if the module grows large, split into `settings.py` (only `BaseSettings`) and `constants.py`, re-export from `settings.py` only if you need a single import path.

```python
from __future__ import annotations

from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict

# --- constants (not from env) ---
DEFAULT_PAGE_SIZE: Final[int] = 50
MAX_PAGE_SIZE: Final[int] = 200
HTTP_TIMEOUT_S: Final[float] = 30.0

# --- env-backed settings ---
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    secret_key: str
    log_level: str = "INFO"
    debug: bool = False

settings = Settings()
```

- Expose a single `**settings**` singleton for `BaseSettings`; inject it explicitly in tests rather than accessing it as a global. Import `**constants**` from the same module (`from my_service.settings import DEFAULT_PAGE_SIZE, settings`) or use the names directly.
- Never commit `.env`; commit `.env.example` with placeholder values.

---

## Async I/O (opt-in)

- For **I/O-heavy** workloads, **async** can improve throughput; use it **only after confirming with the user** that they want an async stack.
- Before committing to async, **verify that required libraries expose async-first or compatible APIs** (e.g. async DB drivers, HTTP clients, FastAPI async routes, Strawberry async resolvers). Do not mix blocking calls in hot async paths without offload/thread pools.
- **Do not force async** without explicit user confirmation.
- When async is confirmed: use `asyncio` + `anyio` for structured concurrency; prefer `async with` / `async for` over manual `gather` for clarity; use `asyncpg` or SQLAlchemy async driver; use `httpx.AsyncClient` for outbound HTTP.

---

## Web and API surfaces

- **REST:** use **FastAPI** (typed dependencies, Pydantic models for request/response where applicable).
- **GraphQL:** use **Strawberry** (typed schema and resolvers; align with the same domain models as REST where it makes sense).

---

## Daemon / long-running processes

- For **daemon-style services** (long-running workers, supervisors), use established patterns: proper signal handling (SIGTERM/SIGINT), structured logging, graceful shutdown, and optionally the `**python-daemon`** library or process managers (systemd, containers) as the project requires.
- Do not daemonize casually in library code; keep entrypoints explicit.

---

## Data models and validation

- Use **Pydantic** (v2) for **validated** settings, API payloads, and boundaries where runtime validation matters.
- Use `**dataclasses`** for **simple immutable or internal** data carriers where validation is not required and typing is enough.
- Choose one primary representation per boundary (avoid duplicating the same shape in three different ad-hoc dicts).

---

## Exception design

- Define a **project-level base exception** (e.g. `AppError`) so callers can catch by family.
- Subclass it for distinct failure modes: `NotFoundError`, `ValidationError`, `UnauthorizedError`.
- Map domain exceptions to HTTP status codes at the **router layer** only — keep service-layer exceptions protocol-agnostic.

```python
class AppError(Exception):
    pass

class NotFoundError(AppError):
    pass

class UnauthorizedError(AppError):
    pass
```

---

## SQL and migrations

- Use **SQLAlchemy** for SQL access and ORM/Core patterns as appropriate.
- Use **Alembic** for **schema migrations**; revision messages and upgrades/downgrades stay reviewable and reversible.

---

## Library packages

- Explicitly define `**__all__`** in `__init__.py` to document the public surface.
- Add an empty `**py.typed**` file to enable type checking for downstream consumers (PEP 561).
- Follow **semantic versioning (semver)** for published packages: **MAJOR.MINOR.PATCH** with clear changelog notes for breaking vs additive changes.

---

## Logging (wide events, structured JSON)

- Prefer **structured JSON logging** (one JSON object per log line or per event batch) so logs are machine-parseable.
- Apply **wide-event** style: emit **one rich event per request/job** (or per major unit of work) with **context fields** (request id, user id, latency, outcome) rather than many tiny unstructured strings.
- Use a structured logging stack (e.g. **structlog** configured for JSON, or `logging` + JSON formatter) consistently; avoid `print` in production paths.

---

## CI pipeline

Minimum CI run for every project:

```bash
uv run ruff check .           # lint
uv run ruff format --check .  # format
uv run ty check               # type check (fallback: uv run mypy src/)
uv run pytest tests/unit/ tests/functional/ tests/interface/
```

Run `integration` tests only against a dev/staging environment, not on every PR.

---

## Testing

- All tests follow **using-pytest**: [using-pytest/SKILL.md](../using-pytest/SKILL.md) (Given/When/Then/Clean, plain functions, business-readable docstrings where required by that skill).

---

## New project checklist

1. Initialize with **uv**; commit lockfile; document `uv sync` and `uv run`.
2. Add **ruff** (lint + format) and **ty** (typecheck); wire into CI using the commands above.
3. Enforce **typing** and `TYPE_CHECKING` imports for type-only deps.
4. Add **pytest** per using-pytest; keep tests fast and layered.
5. For services: **FastAPI** and/or **Strawberry**; **SQLAlchemy** + **Alembic** if persistence applies.
6. Configure **structured JSON** logging with **wide-event** fields; no system Python in docs or scripts.
7. Add `**settings.py`** with `**pydantic-settings**` (`BaseSettings`) and `**Final**` constants as needed; commit `.env.example`, never `.env`.
8. For libraries: add `py.typed` and define `__all__` in `__init__.py`.

