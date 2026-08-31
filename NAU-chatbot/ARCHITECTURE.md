# IIT Academic Assistant Architecture

## 1. System boundary

The repository is a Docker-based modular monolith plus a dedicated inference process. PostgreSQL owns academic truth, Redis owns ephemeral operational state, and Chroma owns derived vector data. No prompt, model, regex, authentication, chat, synchronization, or vector table is added to the academic schema.

```text
Browser
  -> frontend (React/Vite served by nginx)
  -> backend (FastAPI /api/v1)
       -> PostgreSQL (seven academic tables)
       -> Redis (sessions, locks, limits, auth revocation, RAG jobs/status)
       -> Chroma (derived atomic academic chunks)
       -> inference (ESPRIT, Qwen, embedding, reranker adapters)
  -> rag-worker (Redis queue -> PostgreSQL -> inference -> Chroma)
```

Only frontend and backend publish host ports. PostgreSQL, Redis, Chroma, the RAG worker, and inference service remain on an internal Docker network.

## 2. Backend dependency direction

```text
api -> services/application -> domain ports and DTOs
                         -> repositories (ports)
infrastructure -> implements repositories, Redis, Chroma and inference ports
models -> persistence and transport schemas only
```

Routers validate/authorize and delegate. They contain no SQL, Chroma queries, model initialization, recommendation rules, or Redis key construction.

Principal packages under `backend/app`:

- `api/routers`: chat, auth, health, and one admin router per academic entity.
- `core`: typed settings, YAML/prompt loading, security, logging, middleware, dependencies, exceptions.
- `domain`: academic/conversation/RAG/recommendation enums and typed decisions.
- `models/sqlalchemy`: the seven SQLAlchemy 2.x models.
- `models/schemas`: strict Pydantic request/response contracts.
- `repositories/academic`: async, parameterized persistence implementations.
- `services/academic`: catalogue and eligibility reads.
- `services/admin`: transactional CRUD and post-commit change events.
- `services/dialogue`: deterministic-first pipeline stages and response guards.
- `services/recommendation`: dynamic candidate scoring over active DB entities.
- `services/memory`: Redis conversation store and distributed session locks.
- `services/rag`: document/chunk builders, query planner, retrieval, reranking, facts, synchronization.
- `services/llm`: provider interfaces, registry, inference client, and prompt composition.
- `infrastructure`: DB session factory, Redis client, Chroma adapter, HTTP inference adapter.
- `workers`: incremental RAG consumer.

## 3. Academic data model

The schema follows the supplied SQL/UML:

- `parcours 1 -> * formation`
- `formation 1 -> * specialisation`
- `formation 1 -> * formation_element`
- `formation_element 0..1 -> * child formation_element`
- `formation 1 -> * tarif`, optionally scoped to a specialization
- `formation 1 -> * regle_orientation`, optionally scoped to a specialization
- `formation 1 -> * accreditation`

Composite foreign keys ensure a scoped element, tariff, or rule references a specialization belonging to the same formation. Codes and source references are preserved. Application reads default to `actif = true`; admin reads may explicitly include inactive rows. Destructive deletion is refused when dependent data exists, with deactivation offered as the normal lifecycle operation.

Alembic creates the clean seven-table schema. An idempotent seed imports the active official catalogue. A corrective migration/seed step creates active Prépa specialization MP, restricts Prépa admission to Math/Sciences, assigns `SRC_PREPA`, and disables the conflicting legacy Licence GLSI rule. No unsupported Prépa accrediting body is created.

## 4. Transaction and RAG event boundary

```text
Admin request
 -> validate and authorize
 -> AcademicAdminService transaction
 -> PostgreSQL commit
 -> publish AcademicEntityChanged to Redis
 -> return committed entity + indexing state

rag-worker
 -> atomically move queued event to the processing list
 -> set Redis job status RUNNING
 -> load only affected DB entity/formation
 -> build atomic documents
 -> reconcile, embed and upsert/delete Chroma records
 -> acknowledge only after success
 -> set SUCCEEDED, or retry with bounded backoff/dead-letter
```

Publishing happens after commit. A Redis/Chroma failure cannot roll back valid academic data. Failed publication/indexing is logged and exposed through Redis-backed admin status so it can be retried. The single worker restores unacknowledged processing entries after restart; a complete catalogue job also deletes vectors absent from the active PostgreSQL projection.

Event fields are `event_id`, `entity_type`, `entity_id`, `formation_id`, `action`, `occurred_at`, and `attempt`. Queue key: `iit:rag:jobs`; processing key: `iit:rag:processing`; status key: `iit:rag:status:{event_id}`. No synchronization table is created in PostgreSQL.

## 5. RAG architecture

Documents are built from Formation, Specialisation, FormationElement, Tarif, RegleOrientation, and Accreditation. Each entity produces one or more small facts, never one catalogue-sized document.

Deterministic Chroma IDs:

- `formation:{id}`
- `specialisation:{id}`
- `element:{id}`
- `tarif:{id}`
- `orientation:{id}`
- `accreditation:{id}`

Metadata contains scalar Chroma-safe values: entity type/id, formation ID/code, specialization ID/code when present, element type when present, active state, source reference, `updated_at`, and SHA-256 content hash. Unchanged hashes are skipped. Deactivation/deletion removes the corresponding record; formation deactivation/deletion removes records filtered by its formation ID.

Retrieval is:

```text
query -> RAGQueryPlanner -> exact metadata filter -> multilingual E5 candidates
      -> CrossEncoder rerank -> threshold/top facts -> FactBuilder with provenance
```

An empty constrained candidate set stays empty; it never falls back to the whole catalogue. Required admission/fee evidence is selected for the identified formation, not globally. Academic content is delimited as untrusted reference data in model input and cannot issue instructions.

## 6. Dialogue pipeline

One `ChatOrchestrator` coordinates small services:

```text
TurnGate
 -> RawFactExtractor (original message)
 -> NegationDetector
 -> ContextualModifierDetector
 -> PendingSlotResolver
 -> ESPRIT auxiliary NLU
 -> DialogueActDetector
 -> IntentDetector
 -> ConversationMemory update
 -> EligibilityService
 -> RecommendationService
 -> RAGQueryPlanner/Retriever/Reranker
 -> FactBuilder + KnownFacts/ForbiddenAssumptions
 -> Qwen final generation
 -> FactualGuard -> AntiRepetitionGuard -> ResponseLengthGuard
 -> optional ConversionCTA -> committed Redis memory
```

TurnGate responses for greetings, thanks, small talk, profanity, and security requests bypass models and RAG. Original text always outranks ESPRIT. Profile priority is MASTER > LICENCE > PREPA > BAC. Subject state is isolated for SELF, FRIEND, FAMILY, and distinct hypothetical context; a hypothetical never overwrites SELF. Negated interests are removed before positive preference extraction.

Eligibility returns `ELIGIBLE`, `NOT_ELIGIBLE`, or `UNKNOWN` with matched/failed rule IDs and source refs. Recommendation consumes that decision and dynamically scores active formations/specializations using their DB-backed description, elements, interests, profile, goals, rejected offers/domains, and difficulty preferences. A known-ineligible option cannot be the recommendation or receive a pre-registration CTA.

## 7. Conversation state and concurrency

Conversation state is Pydantic-validated JSON in Redis at `iit:chat:session:{uuid}` with configurable TTL. Recent messages are capped. Session reset deletes this key. Idempotent chat responses use `iit:chat:idempotency:{session_uuid}:{key}`.

Each mutation holds a renewable token-owned lock at `iit:lock:session:{uuid}`. Lua scripts extend/release only the owner token. Thus two turns for one session cannot race, while different sessions run concurrently. Model work is bounded by per-model semaphores in the inference service rather than a global API lock.

## 8. Inference boundary

`LLMProvider`, `EmbeddingProvider`, and `RerankerProvider` are application ports. The backend and worker use an authenticated internal HTTP adapter. The inference service owns one central `ModelManager` and exposes internal generate/embed/rerank/health operations.

Configured roles:

- ESPRIT Derja Qwen3 8B v2: auxiliary Tunisian/Arabizi interpretation.
- Qwen3 4B Instruct 2507: constrained classification fallback and final French response.
- multilingual E5 base: embeddings.
- mMARCO MiniLM CrossEncoder: reranking.

Hugging Face adapters load from mounted model paths/cache at runtime, never in routers or image builds. Offline/local-only mode is the production default. Interfaces allow a later vLLM adapter without changing dialogue or RAG services.

## 9. HTTP API

Public/versioned routes:

- `POST /api/v1/chat/session`
- `POST /api/v1/chat`
- `DELETE /api/v1/chat/session/{id}`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- CRUD under `/api/v1/admin/{parcours|formations|specialisations|elements|tarifs|orientation-rules|accreditations}`
- `POST /api/v1/admin/rag/reindex`
- `POST /api/v1/admin/rag/reindex/{formation_id}`
- `GET /api/v1/admin/rag/status`
- `GET /health` and `GET /health/ready`

Readiness reports only dependency names and states for PostgreSQL, Redis, Chroma, and inference.

## 10. Authentication and API security

The prototype admin identity comes only from environment configuration: username plus Argon2id hash. Short-lived JWT access tokens are bearer tokens. Refresh JWTs are stored in HttpOnly cookies and tracked/revoked by JTI in Redis; state-changing cookie endpoints require a double-submit CSRF token. The interface is replaceable by an external identity provider.

Controls include strict schemas/lengths, ORM parameterization, pagination caps, UUID validation, Redis rate limits, request body limits, CORS/TrustedHost configuration, security headers, production exception mapping, constant-time token checks, no raw SQL from requests, no dynamic source fetching, no `eval`/`exec`/shell path, no unsafe deserialization, and redacted structured logs. Frontend rendering uses React text nodes and never renders model HTML.

## 11. Frontend

React/TypeScript/Vite is split into API clients, auth state, chat features, reusable admin CRUD components, layouts, routes, types, and styles. Anonymous chat keeps the current session/history and exposes loading, reconnect/error, reset, mobile, keyboard, focus, and ARIA behavior. Admin screens cover all seven entities with search, filters, pagination, create/edit, activate/deactivate, safe delete, source/timestamp display, and RAG status.

Access tokens remain in memory; refresh uses secure cookies. The UI never exposes prompts, chunks, model identifiers, internal IDs, logs, or stack traces.

## 12. Deployment and failure semantics

Compose services are `frontend`, `backend`, `postgres`, `redis`, `chroma`, `rag-worker`, and `inference`; named volumes are `postgres_data`, `redis_data`, `chroma_data`, and `model_data`. Application images run as non-root users, use multi-stage builds, avoid secrets in layers, and use read-only filesystems/tmpfs where practical.

PostgreSQL is authoritative if RAG is delayed. Redis loss expires anonymous conversations/auth revocations/jobs but does not corrupt academic data. Chroma can be rebuilt completely from PostgreSQL. Inference unavailability makes readiness fail and returns a controlled service-unavailable response for academic model turns; deterministic gates remain implementation-independent.
