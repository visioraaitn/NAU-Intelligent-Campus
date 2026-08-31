# Academic data

## Canonical schema

PostgreSQL contains exactly seven business tables. Authentication, chat, prompts, patterns, models, vectors, chunks, configuration, and RAG synchronization are deliberately outside this schema.

| Table | Purpose | Key relationships |
| --- | --- | --- |
| `parcours` | Top-level study cycle | one-to-many `formation` |
| `formation` | Offered program | belongs to `parcours`; parent of all scoped facts |
| `specialisation` | Option within a formation | belongs to exactly one `formation` |
| `formation_element` | Atomic module, skill, career, domain, certification, language, mobility, tool, opportunity, or information | optional formation/specialisation and optional parent element |
| `tarif` | Indicative/confirmed fee record | belongs to formation, optionally specialisation |
| `regle_orientation` | Structured admission or recommendation criteria | belongs to formation, optionally specialisation |
| `accreditation` | Program accreditation/label | belongs to formation |

Every table has an integer primary key plus `created_at`/`updated_at`; lifecycle-aware entities use `actif`. Codes, positivity checks, date ordering, allowed element types, and specialization scope are enforced in the schema. Composite foreign keys prevent a tariff, rule, or element from referencing a specialization owned by another formation.

Reads default to active records. Deactivation preserves provenance/history and is preferred to deletion. Admin deletion is refused when dependent rows make it unsafe.

## Supported bootstrap

The supplied historical SQL and UML were inspection inputs. A clean deployment uses:

1. Alembic migration `0001_academic_schema` for the seven-table schema;
2. corrective migration `0002_institutional_corrections`;
3. the versioned, idempotent `backend/app/data/academic_seed.yaml` loader.

Run both operations explicitly while the API and RAG worker are stopped. Normal backend startup never mutates the schema or seeds data:

```bash
docker compose run --rm --no-deps backend alembic upgrade head
docker compose run --rm --no-deps backend python -m app.commands.seed_academic
```

The seed upserts by stable business identity in dependency order and reasserts prompt-authoritative corrections on every run. It does not create an eighth table or store seed bookkeeping in PostgreSQL.

Do not execute `iit_academic_db.sql` directly against the production database. It contains historical transitions and conflicting legacy rows; it is not the supported final-state migration chain.

## Current catalogue projection

The seed contains four active parcours and ten active formations:

- Prépa: Cycle Préparatoire (`PREPA_GENERAL`);
- Licence: Informatique, Mécatronique & Systèmes Intelligents, and Systèmes Électriques Intelligents & Énergies Renouvelables;
- Ingénieur: Informatique, Civil, Industriel, Mécanique, and Procédés;
- Architecture: Diplôme National d'Architecte.

Active specializations include Prépa MP; Génie Informatique SDIA, ARSI, and GLID; and the four Licence Informatique options Big Data, GLSI, Cybersécurité, and Systèmes Embarqués/IoT.

Formation elements preserve flyer-backed competencies, careers, domains, certifications, mobility, programme axes, modules, and a small number of public informational facts. They are atomic so eligibility/recommendation and RAG can select only relevant evidence.

## Institutional corrections

Project-supplied institutional rules take precedence over conflicting historical dump rows:

- Prépa has one active MP specialization.
- Prépa admission accepts only Bac Math and Bac Sciences.
- Bac Informatique, Technique, Économie, and Sport are not accepted by the active Prépa rule.
- The conflicting historical Licence GLSI admission rule remains inactive for traceability.
- No Prépa accreditation body is invented.
- The only seeded official accreditation is the Génie Informatique program label EURO-INF, organization ASIIN.

The MP specialization and corrected Prépa admission rule use `PROJECT_INSTITUTIONAL_RULES`. The Prépa formation/program facts use `SRC_PREPA` or the appropriate guide source. This distinction prevents a project correction from being presented as an unsupported public-page claim.

Eligibility is advisory: even when criteria match, final admission requires the institution's application, file review, and validation process. The system must never promise automatic admission.

## Prices and provenance

Seeded fee rows are marked `INDICATIF`, retain currency/source/caveat, and have no fabricated academic year. At the current seed version they include public indicative first-year values for Prépa, Licence Informatique, and Génie Informatique. An operator must verify them before each intake and either update/deactivate them or mark a reviewed record according to institutional policy.

Every factual row that can support an answer should carry `source_ref`. `backend/app/data/source_registry.yaml` documents the known reference ID, title, source type, URL or supplied artifact, and description. It is a version-controlled provenance registry, not an eighth database table.

Source precedence is:

1. explicit current institutional rules supplied for this project;
2. supplied official flyers/current institutional material;
3. current official IIT pages and guides;
4. historical public pages retained only where still useful and non-conflicting.

Never infer missing tuition, program content, eligibility, accreditation, dates, employment guarantees, or contact details. Use `null`/unknown or deactivate stale facts until an authorized source is available.

## Admin write workflow

All academic changes should pass through the authenticated admin API/UI:

```text
strict request -> repository/service transaction -> PostgreSQL commit
               -> post-commit Redis event -> RAG worker -> Chroma
```

Use stable codes; retain `source_ref`; choose the narrowest formation/specialization scope; and deactivate obsolete records instead of rewriting history. After a material edit, verify its RAG status and run a representative chat query.

Direct SQL should be limited to migrations, reviewed repairs, and disaster recovery. If an emergency SQL repair bypasses the API, enqueue a complete RAG rebuild because no post-commit event was emitted.

## Change review checklist

1. Confirm the fact against an authorized, dated source.
2. Check whether it conflicts with `PROJECT_INSTITUTIONAL_RULES`.
3. Preserve the old record by deactivation when historical traceability matters.
4. Validate formation/specialization ownership and structured criteria vocabulary.
5. Treat prices as time-sensitive and include status, currency, period, source, and caveat.
6. Distinguish a program accreditation from an individual certification.
7. Avoid claims of guaranteed admission, employment, salary, visa, or accreditation.
8. Confirm the incremental RAG job succeeds.
9. Review eligibility/recommendation output for affected profiles.
10. Back up PostgreSQL before bulk changes.

## Backup authority

Back up PostgreSQL as the durable catalogue. Chroma is rebuildable and Redis is operational. A valid recovery order is PostgreSQL → Redis/inference availability → Chroma full rebuild. Never restore Chroma alone as if it represented current academic truth.

No migration, seed, import, database query, or data mutation command was executed while this repository was assembled.
