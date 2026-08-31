# Deployment and operations

This runbook describes the intended production workflow for the supplied Compose deployment. The commands are explicit examples for an authorized operator; none were executed during repository creation.

## Capacity and prerequisites

Recommended baseline for the combined seven-service VM:

- 8 modern CPU cores;
- 32 GiB RAM, with 64 GiB preferred for model-loading headroom;
- at least 150 GiB fast storage after accounting for model snapshots, image layers, database backups, and logs;
- an NVIDIA GPU with at least 16 GiB VRAM, with 24 GiB preferred;
- current Docker Engine with Compose v2 and NVIDIA Container Toolkit;
- a TLS reverse proxy on the host or upstream load balancer.

Actual memory depends on the resolved ESPRIT base model, tokenizer caches, sequence lengths, and concurrent workload. Validate peak VRAM/RAM and latency with representative traffic before committing capacity.

## Compose services and persistence

| Service | Image/runtime | Persistent state | Host port |
| --- | --- | --- | --- |
| frontend | nginx + built React assets | none | loopback 8080 |
| backend | Python/FastAPI | none | loopback 8000 |
| postgres | PostgreSQL 16 | `iit_academic_postgres_data` | none |
| redis | Redis 7 with AOF | `iit_academic_redis_data` | none |
| chroma | Chroma | `iit_academic_chroma_data` | none |
| rag-worker | backend image | none | none |
| inference | PyTorch/CUDA | `iit_academic_model_data` | none |

The backend is on both the edge and internal networks. Inference and data services are on an `internal: true` Docker network. The frontend reaches only backend over the edge network.

## First deployment

### 1. Configure secrets and origin

```bash
cd /opt/iit-academic-assistant
cp .env.example .env
chmod 600 .env
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 32
openssl rand -hex 24
openssl rand -hex 24
```

Edit `.env` and assign independent outputs to application/JWT/inference secrets and URL-safe PostgreSQL/Redis passwords. Set the real HTTPS `PUBLIC_BASE_URL`, `CORS_ORIGINS`, and `TRUSTED_HOSTS`. Keep `FRONTEND_BIND_ADDRESS` and `BACKEND_BIND_ADDRESS` at `127.0.0.1` when using a host reverse proxy.

Build the backend and generate the administrator hash:

```bash
docker compose build backend
docker compose run --rm --no-deps backend python -c "from getpass import getpass; from argon2 import PasswordHasher; print(PasswordHasher().hash(getpass('Admin password: ')))"
```

Copy the complete output into the single-quoted `ADMIN_PASSWORD_HASH` value. Validate interpolation before starting anything:

```bash
docker compose config --quiet
```

Do not paste the rendered `docker compose config` output into tickets or logs because it contains secrets.

### 2. Build immutable application images

```bash
docker compose build --pull backend rag-worker inference frontend
docker image inspect iit-academic-backend:local --format '{{.Id}}'
docker image inspect iit-academic-inference:local --format '{{.Id}}'
docker image inspect iit-academic-frontend:local --format '{{.Id}}'
```

For a controlled release, tag/push these image IDs to a private registry and pin both application and third-party images by digest in the release Compose overlay. The local tags in the repository are deployment defaults, not a supply-chain attestation.

### 3. Stage models

Model downloads are intentionally absent from Dockerfiles and runtime startup. On a connected, trusted staging system, acquire the exact approved snapshots, record licenses/revisions/checksums, scan the artifacts, and transfer them to `/srv/iit-model-stage` on the VM.

Expected direct-directory layout:

```text
/srv/iit-model-stage/
  esprit/
  qwen/
  multilingual-e5-base/
  mmarco-reranker/
  hub/                         optional Hugging Face cache, including adapter base
```

If ESPRIT is a PEFT adapter, `esprit/adapter_config.json` identifies its base model. Stage that exact base snapshot in the same Hugging Face cache; local-only startup cannot resolve a missing base.

Copy the staged content to the named volume without starting inference:

```bash
docker volume create iit_academic_model_data
docker compose run --rm --no-deps --user root \
  -v /srv/iit-model-stage:/source:ro \
  inference sh -c 'cp -a /source/. /models/huggingface/'
```

When using direct directories, set:

```dotenv
ESPRIT_MODEL_PATH=/models/huggingface/esprit
QWEN_MODEL_PATH=/models/huggingface/qwen
EMBED_MODEL_PATH=/models/huggingface/multilingual-e5-base
RERANK_MODEL_PATH=/models/huggingface/mmarco-reranker
```

Keep `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. The versioned model policy also enforces `local_files_only: true` and `trust_remote_code: false`.

### 4. Start data services and initialize PostgreSQL

```bash
docker compose up -d postgres redis chroma
docker compose ps
docker compose run --rm --no-deps backend alembic upgrade head
docker compose run --rm --no-deps backend python -m app.commands.seed_academic
```

Migrations and the seed are explicit one-shot operations. Application startup never mutates the schema. Keep the API and RAG worker stopped until both commands succeed.

### 5. Start inference and build the initial RAG collection

```bash
docker compose up -d inference
docker compose ps inference
docker compose logs --tail=200 inference
```

Inference loads ESPRIT and Qwen sequentially to avoid temporary duplicate VRAM pressure, then loads E5 and the reranker. The health check allows a 20-minute startup period. Investigate missing files, incompatible revisions, or GPU memory errors rather than enabling remote downloads in production.

Once `inference` is healthy, start the worker and enqueue the full initial projection:

```bash
docker compose up -d rag-worker
docker compose run --rm --no-deps backend python -m app.commands.reindex_rag
docker compose logs --follow rag-worker
```

In another terminal, wait for the queue to drain and confirm the dead-letter queue remains empty:

```bash
docker compose exec redis redis-cli LLEN iit:rag:jobs
docker compose exec redis redis-cli LLEN iit:rag:processing
docker compose exec redis redis-cli LLEN iit:rag:dead
```

### 6. Start the API and frontend

```bash
docker compose up -d backend frontend
docker compose ps
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:8080/healthz
```

Validate representative Prépa admission, Licence/Ingénieur orientation, fees, programme, careers, and EURO-INF questions through the browser before opening traffic.

## Health and monitoring

`/health` is process liveness. `/health/ready` checks PostgreSQL, Redis, Chroma, and inference and reports only dependency names/states. Route traffic only to ready API instances.

Useful commands:

```bash
docker compose ps
docker compose top
docker compose logs --since=15m backend
docker compose logs --since=15m rag-worker
docker compose logs --since=15m inference
docker stats --no-stream
nvidia-smi
```

Monitor at minimum:

- API request/error/latency and rate-limit counts;
- readiness state and container restarts;
- PostgreSQL connections, storage, locks, and backup age;
- Redis memory, AOF status, evictions, queue length, and dead letters;
- Chroma storage and query latency;
- RAG job failure/retry age;
- inference latency, GPU utilization/VRAM, OOMs, and model readiness;
- host disk/inode/RAM/swap pressure.

Do not enable raw message logging for routine monitoring.

## Database backup

Create a compressed PostgreSQL logical backup with credentials resolved inside the container:

```bash
install -d -m 700 backups
docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges' \
  > "backups/iit_academic_$(date -u +%Y%m%dT%H%M%SZ).dump"
sha256sum backups/iit_academic_*.dump
```

Encrypt and copy backups off-host. Define retention and perform periodic restore rehearsals. PostgreSQL is the only backup required to reconstruct academic facts; keep source/config/model revisions alongside the release manifest.

To test a backup safely, restore it to a separate database/VM. The following in-place restore is destructive and must be used only during an authorized recovery window after preserving the current database:

```bash
docker compose stop frontend backend rag-worker
docker compose exec -T postgres sh -c \
  'pg_restore --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < backups/SELECTED_BACKUP.dump
docker compose up -d backend rag-worker frontend
docker compose run --rm backend python -m app.commands.reindex_rag
```

For a recovery crossing schema versions, restore into the application version that created the backup, then apply reviewed forward migrations.

Redis AOF preserves operational continuity but does not replace PostgreSQL backup. Chroma should be rebuilt from PostgreSQL. Preserve the approved model artifacts and checksums outside the Docker volume.

## Upgrade

1. Back up PostgreSQL and record current image IDs, `.env` checksum, migration revision, model revisions, and Chroma collection name.
2. Review migrations and configuration changes; use a new Chroma collection for embedding/document-format changes.
3. Build or pull pinned images in advance.
4. Stop frontend/backend/RAG worker; keep data services running.
5. Run `alembic upgrade head`, then the idempotent seed as explicit one-shot backend commands.
6. Start backend/worker/frontend, enqueue any required rebuild, and run acceptance checks.

Example maintenance sequence:

```bash
docker compose stop frontend rag-worker backend
docker compose build --pull backend rag-worker inference frontend
docker compose up -d postgres redis chroma inference
docker compose run --rm --no-deps backend alembic upgrade head
docker compose run --rm --no-deps backend python -m app.commands.seed_academic
docker compose up -d backend
docker compose logs --tail=200 backend
docker compose up -d rag-worker frontend
curl --fail http://127.0.0.1:8000/health/ready
```

Do not start backend replicas while an unapplied migration exists. Database migrations are forward operations; an application image rollback may require a database restore if the migration is not backward-compatible.

## Rollback

Retain the previous application image digests and a pre-deployment database backup. If the schema remains backward-compatible, redeploy the previous frontend/backend/worker/inference digests and previous `.env`/config. If not, enter a recovery window and restore the database backup with the matching application version.

For an embedding or document schema change, keep the previous Chroma collection. Roll back by restoring the previous `CHROMA_COLLECTION` and model artifact revisions together. Never point an old embedding model at a collection generated by another model.

## Failure semantics

- PostgreSQL failure blocks academic operations. Restore it first.
- Redis failure blocks safe session mutation, rate limiting, refresh-token tracking, and RAG event delivery. After recovery, perform a complete RAG reconciliation.
- Chroma loss does not lose academic truth. Start a fresh versioned collection and rebuild.
- Inference loss fails readiness and model-dependent turns. Deterministic gates are still code-local, but the deployment should not advertise readiness.
- RAG worker loss delays vector freshness without rolling back committed academic changes. Restart it and inspect queue/dead letters.

Never manually repair Chroma as the first response. Fix PostgreSQL or the processing dependency, then reconcile from source truth.

## Shutdown and destructive cleanup

Graceful stop preserves all named volumes:

```bash
docker compose down
```

Do not use `docker compose down --volumes` in production. It deletes PostgreSQL, Redis, Chroma, and staged-model volumes and is outside normal operations.
