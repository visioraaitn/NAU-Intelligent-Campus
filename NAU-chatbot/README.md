# IIT Academic Assistant

Production-oriented FastAPI and React implementation of the IIT academic assistant. PostgreSQL is the academic source of truth, Redis owns short-lived operational state, Chroma contains rebuildable vectors, and a dedicated GPU inference process owns all Hugging Face models.

The repository was assembled and reviewed statically under the project constraint that no dependency installation, build, migration, model download, service startup, or test command be executed. Run the documented verification sequence on the target VM before release.

## What is included

- Deterministic-first French/Tunisian dialogue orchestration preserving the useful V10 behavior: greetings and security gates, original-message fact extraction, profile/subject memory, negations, contextual and hypothetical scopes, eligibility, recommendation, RAG, guarded final generation, anti-repetition, and conversion CTA policy.
- Strict FastAPI contracts for anonymous chat, refresh-cookie authentication, seven academic CRUD areas, RAG control, liveness, and readiness.
- Exactly seven PostgreSQL business tables: `parcours`, `formation`, `specialisation`, `formation_element`, `tarif`, `regle_orientation`, and `accreditation`.
- Redis sessions, renewable per-session locks, idempotency results, rate limits, refresh-token JTIs, and RAG jobs/status. None of these are stored in the academic database.
- Atomic, provenance-bearing Chroma documents with incremental post-commit indexing and complete rebuild support.
- A React/TypeScript/Vite public chat and protected administration interface, served by non-root nginx.
- Separate non-root API/worker and GPU inference images, plus a seven-service Compose deployment.

See [ARCHITECTURE.md](ARCHITECTURE.md) for component boundaries and [docs/V10_MIGRATION_MAP.md](docs/V10_MIGRATION_MAP.md) for the monolith-to-services migration map.

## Repository map

```text
backend/
  alembic/                 academic schema migrations
  app/api/                 FastAPI routers
  app/core/                settings, security, middleware, errors
  app/data/                versioned academic seed and source registry
  app/domain/              typed academic, conversation, RAG decisions
  app/infrastructure/      PostgreSQL, Redis, Chroma, inference adapters
  app/repositories/        data access boundaries
  app/services/            dialogue, eligibility, recommendation, RAG
  app/workers/             incremental RAG consumer
frontend/                  React/Vite application and nginx runtime
docker-compose.yml         production-shaped local/VM topology
```

## Service topology

```text
browser -> frontend:8080 -> backend:8000
                              |-> postgres:5432
                              |-> redis:6379
                              |-> chroma:8000
                              `-> inference:8010

redis queue -> rag-worker -> postgres + inference + chroma
```

Only frontend and backend publish host ports, both bound to loopback by default. PostgreSQL, Redis, Chroma, RAG worker, and inference stay on an internal Docker network. Put a TLS reverse proxy in front of frontend for production.

## Configuration

Copy the template and replace every `REPLACE_*` value:

```bash
cp .env.example .env
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 24
```

Use the generated values for `APP_SECRET_KEY`, `JWT_SECRET`, `INFERENCE_SERVICE_TOKEN`, PostgreSQL, and Redis as appropriate. Generate the Argon2id admin hash after building the backend image:

```bash
docker compose build backend
docker compose run --rm --no-deps backend python -c "from getpass import getpass; from argon2 import PasswordHasher; print(PasswordHasher().hash(getpass('Admin password: ')))"
```

Place the output in `ADMIN_PASSWORD_HASH` and keep it single-quoted in `.env`. Never commit `.env`. `SECURE_COOKIES=true` requires HTTPS; use `false` only for an explicitly local HTTP environment.

Runtime addresses and secrets are environment settings. Prompt text, regex/pattern sets, dialogue policy, RAG thresholds, and model roles are version-controlled under `backend/app/{prompts,patterns,config}`.

## Model prerequisite

The inference policy is local-only and `trust_remote_code` is disabled. Before starting the stack, stage the complete snapshots for:

- `ESPRIT-Group/ESPRIT-Derja-Qwen3-8B-v2` and its base snapshot when it is a PEFT adapter;
- `Qwen/Qwen3-4B-Instruct-2507`;
- `intfloat/multilingual-e5-base`;
- `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`.

Copy an existing Hugging Face cache or direct model directories into the named `iit_academic_model_data` volume. Detailed commands and adapter caveats are in [DEPLOYMENT.md](DEPLOYMENT.md) and [VM_SETUP.md](VM_SETUP.md).

## Start and initialize

These commands are the intended operator sequence; they were not executed while creating this repository:

```bash
docker compose config
docker compose build
docker compose up -d postgres redis chroma
docker compose run --rm --no-deps backend alembic upgrade head
docker compose run --rm --no-deps backend python -m app.commands.seed_academic
docker compose up -d inference
docker compose ps inference
docker compose up -d rag-worker
docker compose run --rm --no-deps backend python -m app.commands.reindex_rag
docker compose logs --tail=200 rag-worker
docker compose up -d backend frontend
docker compose ps
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:8080/healthz
```

Migrations and seed are deliberately explicit one-shot operations; application startup never mutates the schema. Do not start the RAG worker or enqueue initial indexing until `docker compose ps inference` reports healthy. PostgreSQL remains authoritative while indexing catches up. See [VM_SETUP.md](VM_SETUP.md) for model staging and the fully ordered VM procedure.

## HTTP surface

- `POST /api/v1/chat/session`
- `POST /api/v1/chat` with optional `Idempotency-Key`
- `DELETE /api/v1/chat/session/{session_id}`
- `POST /api/v1/auth/{login,refresh,logout}`
- CRUD under `/api/v1/admin/{parcours,formations,specialisations,elements,tarifs,orientation-rules,accreditations}`
- `POST /api/v1/admin/rag/reindex`
- `POST /api/v1/admin/rag/reindex/{formation_id}`
- `GET /api/v1/admin/rag/status`
- `GET /health` and `GET /health/ready`

FastAPI's OpenAPI UI remains reachable from the loopback-only backend port; nginx does not proxy it from the public frontend. Restrict or disable it at the deployment boundary if institutional production policy requires. The frontend calls `/api/v1` through its same-origin nginx proxy.

## Operations and safety

- Academic data rules and provenance: [ACADEMIC_DATA.md](ACADEMIC_DATA.md)
- RAG indexing, retry, and rebuild: [RAG.md](RAG.md)
- Security model and production checklist: [SECURITY.md](SECURITY.md)
- Deployment, backup, upgrade, and rollback: [DEPLOYMENT.md](DEPLOYMENT.md)
- Fresh Ubuntu/NVIDIA VM procedure: [VM_SETUP.md](VM_SETUP.md)

Do not use the supplied historical SQL dump as a production bootstrap script. Alembic plus the curated, idempotent seed is the supported clean deployment path.
