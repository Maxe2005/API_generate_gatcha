# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this service is

Python/FastAPI microservice that generates Gatcha monster profiles with AI: **Google Gemini** for stats/text (`GEMINI_API_KEY`), **Banana.dev** for pixel-art images (`BANANA_API_KEY`). It is a git submodule of the GatchaApi root repo; approved monsters are transmitted to `API_invocations`. This service does **not** validate caller tokens on its own endpoints — it relies on network isolation.

## Commands

```bash
make env                           # bootstrap .env / .env.docker from examples
make install                       # create .venv + install requirements.txt
make run                           # uvicorn app.main:app --reload on :8000 (needs Postgres/Redis/MinIO up)
make seed / seed-process / seed-dry-run   # seed fixtures/ into Postgres+MinIO (idempotent)

# Standalone docker stack (api + celery + postgres:5434 + redis + minio + pgadmin)
make d-up / d-down / d-logs / d-restart      # uses .env.docker

# When run as part of the whole GatchaApi stack (root docker-compose.yaml)
make global-restart                # rebuild + restart api-generate-gatcha
make global-celery-restart         # rebuild + restart the celery worker
make global-logs / global-celery-logs
```

**Do not run the standalone compose and the root-repo compose at the same time** — same container names/ports.

### Tests

No pytest.ini and no `make test` target. Run with the venv's pytest:

```bash
.venv/bin/pytest tests/test_validation_service.py tests/test_update_events.py   # pure unit tests, no services needed
.venv/bin/pytest tests/test_validation_service.py::TestTypeValidator::test_valid_string  # single test
```

`tests/test_multi_images_workflow.py` is **not** a pytest suite — it's an integration script hitting `http://localhost:8000` (and imports `requests`, which is not in requirements.txt); run it only against a live stack.

No lint/format tooling is configured.

### Database migrations (Alembic)

```bash
make db-alembic-revision MSG="description"   # autogenerate revision
make db-alembic-up                           # upgrade to head (REV=... for a specific rev)
make db-alembic-down REV=-1
make db-shell                                # psql into gatcha_postgres container
```

The scripts run `python -m alembic` on the host, so activate the venv and have Postgres reachable per your `.env` (localhost:5434 with the standalone compose). Note: `init_db()` in `app/models/base.py` also runs `Base.metadata.create_all()` at app startup, so on a fresh DB tables can exist before any migration ran — keep models and Alembic revisions in sync.

### Environment

Config is pydantic-settings (`app/core/config.py`) loading `.env`. Two templates that differ only in hostnames: `.env.example` (localhost, for `make run`) and `.env.docker.example` (docker service names `postgres`/`redis`, used by `docker-compose.yml` via `env_file: .env.docker`). Exception: the Celery broker URL is **hardcoded** to `redis://redis:6379/0` in `app/celery_worker.py` — the worker only resolves inside docker.

## Architecture

Layering: `app/api/v1/endpoints` → `app/services` → `app/repositories` → `app/models` (SQLAlchemy), with `app/schemas` (Pydantic) at the edges and `app/clients` for external systems (Gemini, Banana, MinIO, invocation API). All routers are mounted under `/api/v1` in `app/main.py`: `monsters` (generation + images), `admin`, `transmission`, `external` (import/export), `nano-banana`.

### Monster lifecycle state machine (the core concept)

Every monster lives in `monsters_state` with a state from `MonsterStateEnum` (`app/core/constants.py`): `GENERATED → PENDING_REVIEW → APPROVED → TRANSMITTED`, with `DEFECTIVE` (failed validation, can be corrected) and `REJECTED` (terminal). Valid transitions are declared in `MonsterStateManager.VALID_TRANSITIONS` (`app/services/state_manager.py`) — go through the state manager, never set `state` directly.

**Dual storage model**: in `GENERATED`/`DEFECTIVE` the full monster is a JSON blob in `monsters_state.monster_data`; the transition to `PENDING_REVIEW` restructures it into the relational `Monster`/`Skill` tables and nulls `monster_data`. Code reading monster data must handle both shapes depending on state. Every transition is appended to `StateTransitionModel` history, and admin edits are recorded as events (`update_event` model, `compute_changed_fields` diffing in `app/services/admin_service.py`).

### Async generation flow

`POST /api/v1/monsters/generate` (and `/generate-batch`, and custom image endpoints) enqueue Celery tasks defined in `app/services/tasks.py` (worker entrypoint `app/celery_worker.py`, autodiscovers tasks in `app.services`). Tasks publish progress to Redis pub/sub channel `batch:{batch_id}` (`app/utils/send_messages_utils.py`); WebSocket endpoints (`/api/v1/monsters/ws/{batch_id}` and `/api/v1/monsters/images/ws/{batch_id}`) relay those messages to the front. Celery tasks create their own SQLAlchemy engine/session and wrap async service calls with `asyncio.run` + `nest_asyncio`.

### Storage & validation

- Images go to MinIO buckets `raw-assets`/`game-assets`, linked by the naming convention `game-assets/<stem>.webp` ↔ `raw-assets/monsters/<stem>.png` centralized in `app/utils/image_keys.py`. Monsters support multiple images with one default (`monster_image_model` / `image_service`).
- Fixtures live in `fixtures/` (`monsters/<slug>.json` paired 1:1 with `images/<slug>.png`); `scripts/seed_fixtures.py` (via `make seed`) seeds them idempotently into Postgres+MinIO with deterministic uuid5 monster_ids.
- Validation rules (stat ranges, enums, types) are centralized in `ValidationConstants` in `app/core/constants.py` (aliased as `ValidationRules` in config) and applied by composable validators in `app/services/validation_service.py`. Gemini output failing validation lands the monster in `DEFECTIVE` instead of crashing.
- Transmission to `API_invocations` (`app/clients/invocation_api.py`, `app/services/transmission_service.py`) retries per `INVOCATION_API_*` settings and records attempts/errors on `monsters_state`.

### Docs

`docs/` contains many design/history documents. The load-bearing ones: `MONSTER_LIFECYCLE_STRATEGY.md` (state machine rationale), `VALIDATION_SYSTEM.md`, `MULTI_IMAGES_SYSTEM.md`, `ARCHITECTURE_DESIGN.md`.
