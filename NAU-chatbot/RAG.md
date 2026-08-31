# RAG operations

## Ownership

PostgreSQL is the only academic source of truth. Chroma stores a derived search index and may be deleted and rebuilt. Redis stores indexing events and short-lived status; it is not an academic ledger. No vector, chunk, synchronization, prompt, chat, or model table is added to PostgreSQL.

The RAG worker has one job: consume committed academic-change events, load current rows from PostgreSQL, construct deterministic facts, obtain embeddings from the internal inference service, and reconcile Chroma.

## Indexed documents

Each active entity becomes a small document instead of combining the full catalogue into one prompt:

| Source row | Chroma ID | Typical content |
| --- | --- | --- |
| formation | `formation:{id}` | name, diploma, duration, semesters, description |
| specialisation | `specialisation:{id}` | name/code, parent formation, description |
| formation_element | `element:{id}` | module, skill, career, certification, mobility, or information |
| tarif | `tarif:{id}` | registration, monthly amount/count, currency, status, caveat |
| regle_orientation | `orientation:{id}` | rule name, description, structured criteria |
| accreditation | `accreditation:{id}` | label, organization, description |

Metadata uses Chroma-safe scalar values only: `entity_type`, `entity_id`, `formation_id`, `formation_code`, `specialisation_id`, `specialisation_code`, `element_type`, `source_ref`, `active`, `updated_at`, and SHA-256 `content_hash`.

Only active rows are indexed. The content hash skips unchanged records. Deactivation or deletion removes the relevant vector; changing a formation reconciles its complete active snapshot. IDs are deterministic, so retrying a job is idempotent.

## Retrieval path

```text
user query
  -> typed query plan
  -> exact active/formation/entity filter plus selected-or-formation-level specialisation scope
  -> multilingual E5 query embedding
  -> Chroma cosine candidates
  -> mMARCO CrossEncoder rerank
  -> score threshold and result cap
  -> provenance-bearing facts
  -> delimited untrusted reference section for final generation
```

Intent-to-metadata routing includes fees→`TARIF`, admission→`ORIENTATION_RULE`, accreditation→`ACCREDITATION`, careers→`FORMATION_ELEMENT/METIER`, programme→`FORMATION_ELEMENT/CONTENU_PROGRAMME`, certifications, and international mobility.

If a constrained lookup returns no candidates, it remains empty. It does not fall back to unrelated formations. The final prompt separates static system policy from untrusted user/reference data. Post-generation guards remove unsupported financial, duration, admission, accreditation, certification, mobility, and career claim categories; recommendations themselves come from the structured catalogue/eligibility decision rather than free model choice.

RAG settings are versioned in `backend/app/config/rag.yaml`:

- collection `iit_academic_v1`;
- 24 dense candidates;
- 6 final facts;
- reranker threshold `-10.0`;
- maximum chunk size 1,500 characters;
- indexing batches of at most 64 documents, below the inference API limit.

Change thresholds through reviewed configuration changes, not admin request parameters.

## Incremental indexing

An authorized academic CRUD write follows this boundary:

```text
validate -> PostgreSQL transaction -> commit -> Redis AcademicEntityChanged event
```

The event includes `event_id`, `entity_type`, `entity_id`, `formation_id`, `action`, `occurred_at`, and `attempt`. Publishing after commit ensures an indexing outage cannot roll back correct academic data.

Redis keys:

- queue: `iit:rag:jobs`;
- unacknowledged processing list: `iit:rag:processing`;
- dead letter: `iit:rag:dead`;
- status: `iit:rag:status:{event_id}`;
- recent status index: `iit:rag:recent`.

Statuses are `QUEUED`, `RUNNING`, `RETRYING`, `SUCCEEDED`, or `FAILED`. They expire after `RAG_STATUS_TTL_SECONDS`. The single worker atomically moves a job from queue to processing, acknowledges it only after success, and restores interrupted processing entries at startup. Retries use bounded exponential backoff up to `RAG_MAX_ATTEMPTS`; only an exception class/short summary is exposed, not data or stack traces. Keep exactly one `rag-worker` replica with this reliable-list design.

Inspect the protected API status page or use operational Redis counts:

```bash
docker compose exec redis redis-cli LLEN iit:rag:jobs
docker compose exec redis redis-cli LLEN iit:rag:processing
docker compose exec redis redis-cli LLEN iit:rag:dead
docker compose logs --since=30m rag-worker
```

The Redis service supplies `REDISCLI_AUTH`, so these commands do not place the password on the command line.

## Complete rebuild

Use a complete rebuild after the initial seed, an embedding-model change, a document-format change, suspected vector loss, or Chroma restoration:

```bash
docker compose ps inference chroma redis postgres rag-worker
curl --fail http://127.0.0.1:8000/health/ready
docker compose run --rm --no-deps backend python -m app.commands.reindex_rag
docker compose logs --follow rag-worker
```

The command queues one catalogue reconciliation job. The worker regenerates every active formation snapshot and formation-less global element, skips unchanged hashes, and deletes every Chroma ID absent from the desired PostgreSQL projection. It does not run model work inside the API container. Wait until both queue and processing counts reach zero and recent statuses succeed:

```bash
docker compose exec redis redis-cli LLEN iit:rag:jobs
docker compose exec redis redis-cli LLEN iit:rag:processing
docker compose exec redis redis-cli LLEN iit:rag:dead
docker compose exec redis redis-cli ZREVRANGE iit:rag:recent 0 19
```

The protected admin endpoints can queue all formations or one formation and return event identifiers:

```text
POST /api/v1/admin/rag/reindex
POST /api/v1/admin/rag/reindex/{formation_id}
GET  /api/v1/admin/rag/status
```

## Model or collection migration

Embeddings from different models must not be mixed. For a model/config change:

1. Change `CHROMA_COLLECTION` to a new versioned name such as `iit_academic_v2`.
2. Deploy inference and wait for readiness.
3. Deploy backend and worker with the same collection name.
4. Queue a complete rebuild.
5. Validate representative fee, admission, programme, career, and accreditation questions.
6. Remove the old collection only after acceptance and rollback expiry.

This blue/green collection approach keeps rollback possible. Changing only the model while retaining the old collection is unsupported.

## Failure handling

- **Inference unavailable:** API readiness fails; model-dependent turns receive a controlled dependency error. Do not drain/requeue indexing until inference is healthy.
- **Chroma unavailable:** PostgreSQL writes still commit; jobs retry and may dead-letter. Restore Chroma, then queue a complete rebuild.
- **Redis unavailable:** chat state, token revocation checks, locks, rate limits, and indexing events are unavailable. Restore Redis before accepting traffic; reconcile all formations afterward because post-commit events may have been missed.
- **PostgreSQL unavailable:** academic answers and indexing cannot proceed. Restore the database first; Chroma must never be treated as a database backup.
- **One failed entity:** correct the source row or dependency, then queue that formation from the admin endpoint. Do not manually edit Chroma.

Before clearing a dead-letter queue, preserve it for incident analysis. After the root cause is fixed, prefer a complete PostgreSQL-driven rebuild over replaying untrusted or obsolete raw payloads.

No index, retrieval, embedding, reranking, or failure-recovery command was executed during repository creation.
