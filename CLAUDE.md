# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git workflow (required)

For any piece of work beyond a trivial one-line fix: create a dedicated branch (`feat/...`, `fix/...`, `perf/...`) from `development`, commit in atomic steps with conventional-commit messages in French (`feat:`/`fix:`/`perf:`/`docs:` plus a body explaining the why), then merge back with `--no-ff`. Never commit sizeable work directly on `development` or `master`.

## What this service is

Python/FastAPI microservice that generates Gatcha monster profiles with AI: **Google Gemini** for stats/text (`GEMINI_API_KEY`), **Banana.dev** for pixel-art images (`BANANA_API_KEY`). It is a git submodule of the GatchaApi root repo; approved monsters are transmitted to `API_invocations`. The sensitive routes (`/admin/*`, `/monsters/generate*`, `/nano-banana/*`, `/external/*`, `/transmission/*`, and the mutating `/monsters/images/*` routes) require either a Bearer token verified against `API_authentification`'s `POST /user/verify-token` (`app/clients/auth_api.py`, same contract as the Java services' `AuthInterceptor`) or an `X-Internal-Api-Key` matching `INTERNAL_API_KEY` (machine-to-machine, disabled when unset) — see `app/core/security.py::require_auth`. Read-only GETs and the WebSocket relays stay unauthenticated (browsers can't attach custom headers to a native WebSocket handshake). The verified username is used as the transition actor instead of the client-supplied `admin_name` field, and the caller's token is forwarded to `API_invocations` on transmission (needed when `app.auth.enabled` is on there).

## Commands

```bash
make env                           # bootstrap .env from .env.example (local dev only)
make install                       # create .venv + install requirements.txt
make run                           # uvicorn app.main:app --reload on :8000 (needs Postgres/Redis/MinIO up)
make seed / seed-process / seed-dry-run   # seed fixtures/ into Postgres+MinIO (idempotent)

# Docker — all targets drive the ROOT GatchaApi docker-compose.yaml (no local compose exists)
make up / down / restart / logs / build          # api-generate-gatcha
make celery-up / celery-down / celery-restart / celery-logs   # the celery worker
```

**This service is launched exclusively via the root repo's `docker-compose.yaml`** — in docker, all config comes from the root repo's `.env` (via `env_file`) plus `environment:` overrides in the root compose.

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
make db-shell                                # psql into postgres-generate-gatcha container
```

The scripts run `python -m alembic` on the host, so activate the venv and have Postgres reachable per your `.env` (localhost:5434, the host port exposed by the root stack). Note: `init_db()` in `app/models/base.py` also runs `Base.metadata.create_all()` at app startup, so on a fresh DB tables can exist before any migration ran — keep models and Alembic revisions in sync.

### Environment

Config is pydantic-settings (`app/core/config.py`) loading `.env` (real environment variables take precedence over the file). One template: `.env.example` (localhost hostnames, for `make run` against the root stack's exposed ports). In docker there is no local env file at all (`.env` is dockerignored): the root repo's compose injects everything via `env_file` (root `.env`) + `environment:`. The Celery broker/backend URL is built from `REDIS_HOST`/`REDIS_PORT` in `app/celery_worker.py`.

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
