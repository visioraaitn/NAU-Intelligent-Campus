# V10 migration map

This checklist maps the inspected `iit_v10_final.py` to the modular repository. Line numbers refer to the supplied V10 source. Behavior marked corrected is intentionally not copied verbatim.

| V10 source/feature | New location | Preservation and correction | Planned coverage |
| --- | --- | --- | --- |
| Model IDs/quantization (88–100) | `app/config/models.yaml`, `services/llm/providers.py` | Same four model concepts; typed, replaceable, offline paths. | config/model registry tests |
| Import-time ESPRIT/Qwen loading (105–178) | `infrastructure/inference/model_manager.py`, inference lifespan | One inference process; no router/import loading, Hub inspection, or automatic download. | adapter contract tests |
| `generate_esprit`/`generate_final` (183–250) | provider interfaces + HTTP inference client | Greedy generation and output cleaning retained behind timeouts/semaphores. | provider fake tests |
| Static `IIT_DOCS` (262–580) | `services/rag/document_builder.py` | Removed; atomic facts generated from PostgreSQL with provenance. | document-builder tests |
| E5/CrossEncoder (629–652) | inference embedding/reranker adapters | Metadata-first retrieval, dense candidates, reranking retained; Chroma persisted. | filter/rerank tests |
| `fold_text` (658–663) | `services/dialogue/normalizer.py` | Unicode/diacritic normalization retained; punctuation-aware tokens fix `frais?`/`glid?`. | normalization tests |
| readable logging (685–755) | `core/logging.py`, `services/dialogue/debug_log.py` | Stage names retained in development; secrets and raw sensitive fields redacted. | logging policy inspection |
| subject/session dictionaries (760–826) | `domain/conversation/models.py`, `services/memory/redis_memory.py` | Typed Redis state, TTL, recent history, per-subject state and lock. | persistence/lock tests |
| greeting/how-are-you/thanks/goodbye/reset (831–956) | YAML patterns + `turn_gate.py` | Natural first `Salut`; precedence corrected so thanks/goodbye are reachable. | greeting/small-talk tests |
| security patterns (857–876) | `patterns/security.yaml`, `security_gate.py` | Fast refusal preserved; layered validation replaces blacklist-only trust. | injection tests |
| profanity gate (880–896) | `patterns/insults.yaml`, `turn_gate.py` | Runs before memory/models/RAG and does not mutate academic state. | insult/no-mutation tests |
| social prefix stripping (921–967) | `turn_gate.py` | Mixed greeting + academic question retained. | mixed-turn tests |
| first `Salut` guard (1003–1007) | `turn_gate.py`, `orchestrator.py` | Exactly first assistant response only. | first-response tests |
| subject detection (1014–1026) | `subject_detector.py` | SELF/FRIEND/FAMILY/HYPOTHETICAL retained; follow-ups keep active non-SELF subject until closed. | hypothetical isolation tests |
| profile detection (1029–1079) | `raw_fact_extractor.py` | Highest explicit level wins; questions about catalogues do not imply ownership; explicit corrections supported. | Licence > Bac tests |
| Bac/average/math extractors (1082–1171) | `raw_fact_extractor.py` | Original message deterministic and evidence-bearing. | Bac Sport/Eco/grade tests |
| interests (1174–1187) | `raw_fact_extractor.py` after `negation_detector.py` | Vocabulary retained; negated interests cannot become positive. | negated-interest tests |
| Licence specialty/target (1190–1219) | `raw_fact_extractor.py` | Nursing and other explicit degrees preserved without assuming engineering eligibility. | profile tests |
| ALL/OTHER/MORE (1236–1249) | `contextual_modifier.py` | Prior factual intent preserved for short modifiers. | fees ALL/MORE tests |
| rejected offers/domains (1252–1270) | `negation_detector.py`, conversation state | Persisted and excluded from immediate recommendations. | rejection tests |
| rank/apply facts (1273–1358) | `profile_resolver.py`, memory service | MASTER > LICENCE > PREPA > BAC retained; subject isolation/corrections fixed. | priority/correction tests |
| ESPRIT prompt (1363–1459) | `prompts/esprit_nlu.txt`, `esprit_nlu.py` | Auxiliary faithful interpretation only; never source of personal facts. | fake-provider precedence tests |
| dialogue acts (1464–1560) | `patterns/intents.yaml`, `dialogue_act_detector.py`, classifier prompt | Deterministic first, schema-constrained Qwen fallback. | dialogue-act tests |
| multi-intents (1565–1683) | `intent_detector.py` | Multi-intent and original-message priority retained. | multi-intent tests |
| slots/`10 w 9` (1688–1819) | `pending_slot_resolver.py` | One progressive question; contextual average/math parsing retained; unrelated user questions are answered. | pending-slot tests |
| eligibility engine (1824–1907) | `services/eligibility/eligibility_service.py` | DB rule evaluation returns status, matched/failed IDs and refs; no LLM rules. Active-student and plan propagation bugs fixed. | Prepa/Bac Sport/Eco tests |
| recommendation (1916–2054) | `services/recommendation/recommendation_service.py` | Dynamic active catalogue and academic elements replace hard-coded AI→GLID/defaults; alternatives are re-evaluated. | dynamic recommendation tests |
| detail expansion (2059–2090) | `detail_policy.py` | Covered topics/detail levels retained without restarting recommendation. | novelty/detail tests |
| candidate filtering (2095–2173) | `metadata_filters.py`, `query_planner.py` | Exact formation/spec/element filters retained and expanded; empty means no results. | metadata filter tests |
| semantic search/rerank (2176–2208) | Chroma repository, retriever, reranker | Thresholds and stable candidate budgets added. | retrieval contract tests |
| critical facts (2211–2293) | `fact_builder.py` | Required evidence is formation-specific and cannot be truncated by unrelated facts. | grounding tests |
| allowed facts (2298–2311) | `domain/rag/schemas.py`, `fact_builder.py` | Structured facts keep entity/source provenance. | provenance tests |
| response modes/topics (2316–2357) | `response_policy.py` | SOCIAL/FACT/RECOMMENDATION/DETAIL budgets retained. | length tests |
| CTA instruction/policy (2360–2370, 2863–2931) | `conversion_cta.py`, `config/dialogue.yaml` | Funnel/cadence retained; factual follow-ups, hypothetical and ineligible turns suppress CTA; URL used only if configured. | no-duplicate CTA tests |
| known/forbidden facts (2374–2415) | `known_facts_builder.py` | UNKNOWN remains forbidden to guess; admission/employment promises always forbidden. | prompt-context tests |
| final system/turn prompts (2420–2602) | `prompts/final_answer.txt`, `prompt_composer.py` | Delimited policy/user/memory/known/academic/forbidden sections; DB/RAG is untrusted data. | prompt-injection tests |
| greeting/language/factual guards (2635–2731) | `services/dialogue/guards/` | Deterministic claim policy and grounding; every model rewrite is revalidated. | factual guard tests |
| deterministic fallback/minimum content (2733–2824) | `fallback_response.py`, `orchestrator.py` | Useful answer cannot be replaced by CTA. | fallback tests |
| novelty guard (2827–2860) | `guards/anti_repetition.py` | Last response/covered topics retained; no unnecessary extra LLM chain. | repeated-intro tests |
| six-line compaction (2934–2956) | `guards/length.py` | Default 4–6 short lines and explicit detail allowance retained. | response-mode tests |
| topic/memory update (2959–3034) | `topic_tracker.py`, Redis memory | Updates only after accepted final answer; per-subject conversion state. | memory tests |
| monolithic pipeline (3039–3351) | `chat_orchestrator.py` | Ordered dependency-injected stages with per-session transaction/lock. | orchestrator tests |
| inline self-tests (3356–3372) | `backend/tests/unit` and `integration` | Assertions moved out of imports and expanded; files are written but not run now. | all requested suites |
| Gradio handlers/state/UI (3377–3436) | FastAPI chat routes + React chat feature | Anonymous Redis session and responsive accessible UI. | API/frontend tests |
| global queue/public debug launch (3438–3442) | per-session Redis locks + inference semaphores + Compose | Different users concurrent; no share tunnel/debug stack exposure. | concurrency tests |

## Explicit removals

- Runtime `pip install`, network/model download, import-time GPU/model initialization, inline test execution, and Gradio launch.
- Unsupported MP ministry accreditation text. MP is active and institutionally validated per project policy, but no accrediting organization is named without sourced data.
- Old standalone `LICENCE_GLSI`, `INGENIEUR_GLID`, and `INGENIEUR_ARSI` as active formations. Current specializations live under `LICENCE_INFO` and `INGENIEUR_INFO`, including SDIA.
- Static market documents from the academic index. Any future market source must use a separately governed non-academic connector/index.
- Raw user-message logging and unrestricted whole-corpus fallback.
