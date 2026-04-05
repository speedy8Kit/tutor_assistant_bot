# CLAUDE.md

Guidance for Claude Code when working in this repository.

---

## Project Overview

Telegram bot for private tutors: manages appointments, student reminders, and schedules.
Stack: Python 3.12, python-telegram-bot (async), PostgreSQL 15, Redis 7, Poetry, Docker.

---

## ABSOLUTE RULES

These rules are non-negotiable and override all default behaviors.

1. **Never run Python on the host.** No `python`, `poetry run`, `pip install`, or `poetry install` on the host machine.
2. **Never install packages manually** inside a running container. All dependencies must be declared in `pyproject.toml` and installed via the Dockerfile build.
3. **Never modify a running container** as a substitute for updating source files. The container is ephemeral — manual changes are lost on restart.
4. **Always assume the Docker environment.** Every command suggestion must use `docker-compose` or `docker exec`.
5. **Never suggest `pip install` or `apt install`** outside of the Dockerfile.

Violation of any rule above produces an unreproducible environment.

---

## Services

| Service | Container name | Purpose |
|---|---|---|
| `dev` | `tutor-bot` | Interactive shell for development |
| `inference` | `tutor-bot-inference` | Runs the bot (`python -m tutor_assistant`) |
| `postgres` | `tutor-postgres` | PostgreSQL 15 database |
| `redis` | `tutor-redis` | Redis 7 cache / job queue |

The `dev` container mounts the repo at `/app` (live reload of source edits — no rebuild needed for `.py` changes). The `inference` container does **not** mount the repo.

---

## Canonical Commands

### Start the stack

```bash
# Start all services (dev shell + bot + postgres + redis)
docker-compose up -d

# Attach to the dev shell
docker exec -it tutor-bot bash
```

### Run the bot (inference)

```bash
docker-compose up inference
```

### Execute a one-off command inside the container

```bash
docker exec tutor-bot <command>

# Examples
docker exec tutor-bot python -m tutor_assistant
docker exec tutor-bot pytest
docker exec tutor-bot alembic upgrade head
```

### Rebuild the image

```bash
docker-compose build
# or for a specific service
docker-compose build dev
```

### Stop and clean up

```bash
docker-compose down          # stop containers, keep volumes
docker-compose down -v       # stop containers + delete volumes (destructive)
```

---

## When a Rebuild Is Required

Rebuild the container image whenever any of the following change:

| Changed file | Rebuild required |
|---|---|
| `Dockerfile` | Yes — always |
| `pyproject.toml` | Yes — dependency graph changed |
| `poetry.lock` | Yes — pinned versions changed |
| `*.py` source files | **No** — volume mount reflects changes immediately |
| `.env` / `ConfigDev.toml` | **No** — loaded at runtime |

**Rebuild command:**
```bash
docker-compose build && docker-compose up -d
```

Claude must explicitly tell the user to rebuild when a change to a rebuild-triggering file is made.

---

## Development Workflow

```
Edit source → (rebuild if needed) → exec command in container → observe output
```

1. Edit files on the host with your editor.
2. If `pyproject.toml`, `poetry.lock`, or `Dockerfile` changed → rebuild.
3. Run commands via `docker exec tutor-bot <cmd>` or inside the attached shell.
4. Source changes in `src/` are reflected immediately via the volume mount.

---

## Dependency Management

All dependencies are managed through Poetry inside the container.

```bash
# Add a new dependency (run inside container)
docker exec tutor-bot poetry add <package>

# After adding, commit pyproject.toml and poetry.lock, then rebuild
docker-compose build
```

Never run `poetry install` or `pip install` on the host.

---

## Testing

All tests run inside the container.

```bash
# Run all tests
docker exec tutor-bot pytest

# Run a single test
docker exec tutor-bot pytest tests/path/to/test_file.py::test_name

# Run with coverage
docker exec tutor-bot pytest --cov=tutor_assistant
```

### Testing guidelines

- Use `pytest` as the test runner.
- Mock all external services (Telegram API, PostgreSQL, Redis) — do not depend on live services in unit tests.
- Integration tests that require PostgreSQL or Redis should use the services defined in `docker-compose.yml` and run inside the container.
- Test files live in `tests/` at the repo root.

---

## Linting and Formatting

Run inside the container:

```bash
docker exec tutor-bot black src/ scripts/
docker exec tutor-bot isort src/ scripts/
docker exec tutor-bot ruff check src/ scripts/
docker exec tutor-bot mypy src/
```

Or in one pass via pre-commit (still inside the container):

```bash
docker exec tutor-bot pre-commit run --all-files
```

---

## Database Migrations (Alembic)

```bash
# Apply all pending migrations
docker exec tutor-bot alembic upgrade head

# Create a new migration
docker exec tutor-bot alembic revision --autogenerate -m "description"
```

---

## Environment Variables

Declared in `.env` (copy from `.env.example`). Loaded automatically by `docker-compose`.

| Variable | Description |
|---|---|
| `BOT_TOKEN` | Telegram bot token |
| `DATABASE_URL` | `postgresql+asyncpg://abmine:abmine@postgres:5432/tutor_bot` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `APP_CONFIG_FILE` | Path to TOML config (default: `ConfigDev.toml`) |

---

## Architecture

```
src/tutor_assistant/
├── config.py        # AppConfig — TOML config loaded via APP_CONFIG_FILE
├── bot.py           # TutorBot — builds Application, wires handlers
├── init_bot.py      # Low-level bot initialization
├── database/        # SQLAlchemy async models + engine (in progress)
├── handlers/        # Telegram update handlers (in progress)
├── core/            # Business logic (in progress)
├── utils/
│   └── logger.py    # get_logger() — JSON or text logger
└── __main__.py      # Entry point
```

**Config flow:** `.env` → `AppConfig` (from TOML) → frozen dataclasses (`BotConfigs`, `MainConfig`).

**Async:** All handlers and DB calls are async. `telegram.ext.Application` handlers must be `async def`.

---

## Anti-Patterns — Never Do These

| Anti-pattern | Correct alternative |
|---|---|
| `python script.py` on host | `docker exec tutor-bot python script.py` |
| `poetry install` on host | Declare in `pyproject.toml`, rebuild image |
| `pip install <pkg>` anywhere | `docker exec tutor-bot poetry add <pkg>`, then rebuild |
| `apt install` on host or in running container | Add to `Dockerfile`, rebuild |
| Editing files inside the container | Edit on host (volume mount syncs automatically) |
| Running tests on host | `docker exec tutor-bot pytest` |

---

## Assistant Response Rules

When suggesting commands or changes, Claude must:

1. Always use `docker exec tutor-bot <cmd>` or `docker-compose` — never bare host commands.
2. Explicitly state "**Rebuild required:** `docker-compose build && docker-compose up -d`" whenever `Dockerfile`, `pyproject.toml`, or `poetry.lock` is modified.
3. Never suggest `pip install`, `poetry install`, or `apt install` outside of Dockerfile context.
4. Assume the `dev` container (`tutor-bot`) is running when suggesting exec commands.
5. When adding a new dependency, always remind the user to commit `pyproject.toml` + `poetry.lock` and rebuild.
