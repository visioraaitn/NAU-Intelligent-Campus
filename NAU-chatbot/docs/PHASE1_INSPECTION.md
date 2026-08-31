# Phase 1 inspection baseline

This document records the static inspection performed before implementation. No package was installed, model downloaded, application launched, migration executed, container started, external service contacted, or test run.

## Supplied artifacts

| Artifact | Static finding |
| --- | --- |
| `iit_v10_final.py` | 3,442-line Colab/Gradio prototype combining package installation, model loading, static RAG, dialogue logic, memory, tests, logging, and UI in one import-time script. |
| `iit_academic_db.sql` | 838-line PostgreSQL script that builds a historical schema, enriches it from official-source references, then projects active data into seven final academic tables. |
| `download (1).jfif` | UML for the same seven academic entities and their relationships. |
| Workspace | Empty: no files, hidden configuration, Git repository, or existing changes were present. |

Artifact SHA-256 values observed during inspection:

- SQL: `0932401782B729785070C0FE43E4C9DD2156E55FC474819FDB53DF6C1D23C295`
- V10 Python: `CD797DD96E4819EA728710740420945506051702FAFB10A9802C8840B70AC686`
- UML image: `E7FB3ABDF13B0B234FBE7E7E8652D3166C30D192648F4C2F98E076A54790E7E5`

## Final academic model found in SQL and UML

The target database contains only these domain tables:

1. `parcours`
2. `formation`
3. `specialisation`
4. `formation_element`
5. `tarif`
6. `regle_orientation`
7. `accreditation`

The SQL final projection is defined at source lines 652–709, populated at lines 711–791, indexed at lines 793–805, and renamed at lines 825–828. It uses stable codes, source references, active flags, timestamps, a self-referencing element hierarchy, and composite foreign keys so an optional specialization scope always belongs to the same formation.

The UML confirms:

- one parcours proposes zero or more formations;
- one formation contains zero or more specializations;
- elements, tariffs, and orientation rules belong to a formation and may be narrowed to one specialization;
- one formation may have many accreditations;
- formation elements may have child elements.

The SQL permits a global `formation_element` with no formation for the IIT contact fact. This is a deliberate extension of the conceptual UML. `Tarif.source_ref` is also present in SQL even though it is omitted from the diagram.

## Current active catalogue found in SQL

Four parcours are active: Prépa, Licence, Cycle Ingénieur, and Architecture.

Ten formations are active:

- `PREPA_GENERAL`
- `LICENCE_INFO`
- `LICENCE_MECATRONIQUE_SI`
- `LICENCE_ELEC_SEIER`
- `INGENIEUR_INFO`
- `INGENIEUR_CIVIL`
- `INGENIEUR_INDUSTRIEL`
- `INGENIEUR_MECANIQUE`
- `INGENIEUR_PROCEDES`
- `ARCHITECTURE_DNA`

Current specializations that must remain active include:

- Génie Informatique: `SDIA`, `ARSI`, `GLID`.
- Licence Informatique: `LIC_INFO_BIG_DATA`, `LIC_INFO_GLSI`, `LIC_INFO_CYBER`, `LIC_INFO_IOT`.

The source contains 246 derived formation-element rows spanning modules, programme content, competencies, careers, activity domains, certifications, languages, mobility, opportunities, and information. Three indicative tariffs exist for Prépa, Licence Informatique, and Génie Informatique. The only sourced accreditation is EURO-INF/ASIIN for Génie Informatique.

## Institutional corrections required

The explicit project rules override conflicting legacy rows:

- `ADMISSION_PREPA` must accept only Bac Math and Bac Sciences. Informatique, Technique, Économie/Gestion, and Sport must be deterministically rejected for this formation.
- Active specialization `MP` must be created under `PREPA_GENERAL`.
- `PREPA_GENERAL.source_ref` must be corrected to `SRC_PREPA`.
- No Prépa accreditation organization may be invented. The statement that MP is institutionally validated is represented as an institutional rule with project provenance, not as an `accreditation` row with a fabricated body.
- The newer Licence Informatique rule and current specialization catalogue take precedence over the old standalone GLSI formation assumptions.
- Old GLSI-specific modules/facts that remain useful must be scoped to `LIC_INFO_GLSI`, not leaked to every Licence Informatique specialization.
- Bac Sport is handled with strict admission-whitelist semantics. Absence from an accepted list is a deterministic mismatch, not an invitation to promise manual acceptance.

## V10 behavior worth preserving

V10’s useful contract is architectural rather than framework-specific:

- original-message facts outrank model paraphrases;
- ESPRIT is an auxiliary Derja/Arabizi language interpreter only;
- highest explicit degree wins;
- SELF, FRIEND, FAMILY, and HYPOTHETICAL memory are separate;
- pending slots and contextual answers such as `10 w 9` are understood;
- `ALL`, `OTHER`, and `MORE` preserve the preceding intent where appropriate;
- negated domains/offers are remembered and not immediately resold;
- eligibility precedes recommendation;
- metadata-constrained retrieval precedes embeddings and reranking;
- Qwen verbalizes structured decisions and grounded facts;
- known facts and forbidden assumptions are supplied explicitly;
- factual, novelty, length, first-greeting, and CTA cadence guards run after generation;
- social, profanity, and security turns bypass expensive model/RAG work;
- readable stage-oriented debug logs are valuable in development.

## V10 defects intentionally not carried forward

- import-time package installation, network calls, GPU checks, model downloads, self-tests, and UI launch;
- `trust_remote_code=True` as an unconditional default;
- static `IIT_DOCS` and in-memory embeddings;
- hard-coded GLSI/GLID/ARSI-only catalogue and recommendation decisions;
- unsupported claims that MP is accredited by a ministry;
- in-process Gradio state and one global request queue;
- public `share=True`, debug mode, raw stack/error exposure, and unredacted message logging;
- blacklist-only prompt-injection defense;
- negated interests accidentally becoming positive preferences;
- short hypothetical/friend follow-ups contaminating SELF memory;
- unrestricted RAG fallback when a metadata candidate set is empty;
- CTA insertion during ordinary factual follow-ups;
- post-guard rewrites that are not revalidated.

## Migration posture

The supplied SQL remains the historical reference and must not be executed directly by the new application because it is destructive and not safely rerunnable. The implementation translates its final model and active data into clean Alembic migrations plus an idempotent seed process. PostgreSQL remains academic-only; Redis owns conversation/auth/queue state and Chroma owns derived vectors.
