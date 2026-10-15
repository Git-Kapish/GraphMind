# Architectural & Gate Decisions Log (docs/DECISIONS.md)

| Date | Milestone | Decision | Context & Rationale | Status |
|---|---|---|---|---|
| 2026-10-15 | M0 | Adopt Python 3.12 with uv and Pydantic v2 | Python 3.12 is fully compatible with pgvector, psycopg, neo4j, and edgartools; managed by uv. | Approved |
| 2026-10-15 | M0 | Ollama local runtime with nomic-embed-text & llama3.2 | $0 model spend constraint; local-first; nomic-embed-text matches 768-d pgvector configuration. | Approved |
| 2026-10-15 | M0 | PostgreSQL as authoritative source of truth | Neo4j is a rebuildable projection from extraction_observations. | Approved |
| 2026-10-15 | M2 | Select `qwen2.5:3b` as extraction model | In Model Selection Gate (§6.1), Qwen 2.5 3B achieved 43.55s/chunk vs Llama 3.2 3B at 207.91s/chunk (~4.8x faster on CPU), with 0% timeouts, 100% JSON validity, and 100% quote match. | Approved |
| 2026-10-15 | M2.5 | Go/No-Go Gate: Proceed to M3 (Graph Advantage Confirmed) | In M2.5 Thin Vertical Slice (§0 rule 13, §14), Graph Retrieval scored 10/10 (100%) vs Vector Baseline at 8/10 (80%), retrieving verified multi-hop paths (e.g. Q01: NVIDIA and Microsoft shared market categories) that vector baseline missed. Gate criterion PASSED (GO). | Approved |
| 2026-10-15 | M3 | Entity Resolution & Graph Projection Hardened | Multi-tier candidate resolution (exact -> alias -> token Jaccard -> embedding) benchmarked across 110 hand-verified enterprise pairs with 100% Precision, 100% Recall, 0 False Merges. Rebuild script verified with 100% concordance (267 nodes, 384 edges) and idempotency. | Approved |
| 2026-10-15 | M4 | Vector Index & Pre-Routing Retrieval Evaluation | Pre-routing retrieval benchmark executed over 40 hand-verified questions: Recall@5 = 65.0%, Recall@10 = 75.0%, MRR = 0.5346 at 84.2 ms avg latency. Verified pgvector 768-d HNSW indexing, bidirectional provenance mapping, and chunks.entity_ids synchronization. | Approved |



## Model Selection Gate Benchmark (§6.1)

- **Hardware Profile:** 13th Gen Intel Core i5-13500H (12 cores / 16 threads), 16 GB RAM, CPU-only execution (Intel Iris Xe iGPU).
- **Benchmark Corpus:** SEC 10-K Item 1 chunks with high relation cues (`supplier`, `manufactur`, `compet`).
- **Results Summary:**

| Candidate Model | JSON Valid Rate | Quote Match Rate | Total Relations | Avg Latency (CPU) | Timeout Rate (>240s) | Selection Outcome |
|---|---|---|---|---|---|---|
| `llama3.2:latest` (3.2B) | 100.0% | 100.0% | 1 | 207.91 s/chunk | 66.7% | Rejected (Excessive CPU latency & timeouts) |
| `qwen2.5:3b` (3.09B) | 100.0% | 100.0% | 1 | 43.55 s/chunk | 0.0% | **WINNER (Selected)** |

**Key Findings:**
1. Qwen 2.5 3B demonstrates superior instruction following with concise JSON emission on dense SEC filing text, avoiding the generation loops and token bloat that caused Llama 3.2 3B to exceed 240 seconds per chunk on CPU.
2. Qwen 2.5 3B correctly resolved company self-references ("we" -> filer name) and extracted verbatim quotes verified at score 1.0.
3. Timeout configuration for extraction in `config/settings.yaml` calibrated to 120.0s, giving ample margin over the 43.55s average.

## Milestone M2.5: Thin Vertical Slice & Go/No-Go Gate Decision (§0 rule 13, §14)

- **Date:** 2026-10-15
- **Objective:** Verify whether Graph Retrieval returns correct, evidenced paths that Vector Baseline misses on at least 1 verified multi-hop question before committing to M3 hardening.
- **Corpus State:** 592 SEC 10-K chunks embedded with `nomic-embed-text:latest` (768-d pgvector), 265 canonical entities, 391 Neo4j relationships.
- **Results on 10 Hand-Verified Benchmark Questions:**

| Question ID | Category | Hops | System A (pgvector Top-5) | System B (Neo4j Graph) | Outcome / Advantage |
|---|---|---|---|---|---|
| Q01 | multi_hop | 2 | FAIL | PASS | **[+] GRAPH WINS** (Vector failed to connect shared market taxonomy) |
| Q02 | multi_hop | 2 | PASS | PASS | = Both answered (AMD -> TF AMD Penang -> Malaysia) |
| Q03 | multi_hop | 2 | PASS | PASS | = Both answered (AMD -> AMD Japan -> Japan) |
| Q04 | multi_hop | 2 | PASS | PASS | = Both answered (AMD -> AMD ROU -> Romania) |
| Q05 | multi_hop | 2 | PASS | PASS | = Both answered (AMD -> AMD India -> India) |
| Q06 | multi_hop | 2 | PASS | PASS | = Both answered (NVIDIA -> Worldwide <- Microsoft) |
| Q07 | single_hop | 1 | PASS | PASS | = Both answered (Broadcom -> VMware/CA/Symantec) |
| Q08 | single_hop | 1 | FAIL | PASS | **[+] GRAPH WINS** (Vector retrieved general business descriptions instead of headquarters) |
| Q09 | single_hop | 1 | PASS | PASS | = Both answered (Microsoft -> Redmond, Washington) |
| Q10 | single_hop | 1 | PASS | PASS | = Both answered (NVIDIA -> Jensen Huang / founders) |

- **Summary Scores:**
  - **System A (Vector Baseline):** 8/10 (80.0%)
  - **System B (Graph Retrieval):** 10/10 (100.0%)
  - **Multi-Hop Questions Won by Graph:** 1 (Q01)
  - **Single-Hop Questions Won by Graph:** 1 (Q08)
- **Gate Evaluation:**
  - PRD Criterion: *"Does graph retrieval return correct, evidenced paths that vector baseline misses on at least 1 verified multi-hop question?"*
  - Answer: **YES** (Graph Retrieval successfully resolved Q01 multi-hop path connecting NVIDIA and Microsoft through `computer hardware companies`, which vector top-5 missed).
- **Formal Gate Decision:** **GO (PASSED)**. Proceed to Milestone M3 (Entity Resolution & Graph Projection Hardening).

## Milestone M3: Entity Resolution & Graph Projection Acceptance (PRD §8, §9, §14)

- **Date:** 2026-10-15
- **Objective:** Candidate matching, review queue, merge history auditing, graph writer, and rebuild command.
- **Evaluation Dataset:** 110 hand-verified enterprise entity pairs (`benchmarks/labels/resolution_pairs.jsonl`), including 62 true merges (legal suffixes, acronyms, known aliases) and 48 hard negatives (token overlap, competitors, distinct subsidiaries).
- **Benchmark Results (`benchmarks/results/resolution_benchmark.json`):**

| Metric | Target | Measured Result | Status |
|---|---|---|---|
| Total Labeled Pairs | $\ge 100$ | 110 | PASS |
| False Merges (FP) | 0 | 0 | **PERFECT (100% Precision)** |
| Missed Merges (FN) | Low | 0 | **PERFECT (100% Recall)** |
| F1 Score | $> 90.0\%$ | 100.0% | PASS |
| Overall Accuracy | $> 90.0\%$ | 100.0% | PASS |

- **Graph Projection & Concordance:**
  - PostgreSQL Canonical Entities: **267**
  - PostgreSQL Aggregated Evidenced Edges: **384**
  - Neo4j Projected `:Entity` Nodes: **267** (100% match)
  - Neo4j Projected Relationships: **384** (100% match)
  - Entity Embedding Coverage: **267/267** (100% 768-d pgvector embeddings generated via `nomic-embed-text:latest`)
  - Rebuild Elapsed Time: **0.92s**
  - Idempotency Test: Passed (Consecutive rebuilds yield identical 267 nodes and 384 edges)
  - Provenance Tracing: Verified (100% of Neo4j edges map to valid `observation_ids` and `chunks`).

## Milestone M4: Vector Index & Pre-Routing Retrieval Evaluation (PRD §7.2, FR-2.3)

- **Date:** 2026-10-15
- **Objective:** Verify pgvector HNSW indexing, bidirectional provenance helpers, entity mention linking, and evaluate Recall@3, Recall@5, and Recall@10 before starting Router development.
- **Evaluation Dataset:** 40 hand-verified `(question, gold_chunk_ids)` pairs (`benchmarks/questions/retrieval_eval_pairs.jsonl`) across 6 enterprise filers.
- **Benchmark Results (`benchmarks/results/retrieval_eval_m4.json` & `docs/retrieval_eval.md`):**

| Metric | Target | Measured Result | Status |
|---|---|---|---|
| Total Questions | $\ge 40$ | 40 | PASS |
| Recall@3 | Baseline | 55.00% (22/40) | EVALUATED |
| Recall@5 | $\ge 60.0\%$ | **65.00%** (26/40) | **PASS** |
| Recall@10 | $\ge 70.0\%$ | **75.00%** (30/40) | **PASS** |
| MRR (Mean Reciprocal Rank) | $> 0.40$ | **0.5346** | **PASS** |
| Average Latency | $< 500$ ms | **84.2 ms** | **PASS** |

- **Performance by Filer:**
  - AMD: 85.7% Recall@5 (6/7)
  - NVDA: 85.7% Recall@5 (6/7)
  - INTC: 85.7% Recall@5 (6/7)
  - MSFT: 66.7% Recall@5 (4/6) [100% Recall@10]
  - MU: 33.3% Recall@5 (2/6) [66.7% Recall@10]
  - AVGO: 28.6% Recall@5 (2/7)
- **Key Architectural Insight:**
  - Descriptive, narrative topical questions achieve high recall in pure vector retrieval (85.7% for AMD/NVDA/INTC).
  - Fine-grained entity lists and cross-border subsidiaries (AVGO/MU Exhibit 21) show lower rank in pure vector retrieval, directly evidencing the need for graph-guided traversal in hybrid retrieval.
- **Gating Decision:** **PASSED**. PRD FR-2.3 pre-routing retrieval evaluation certified. Proceed to Milestone M5 (Query Templates & Vector Retrieval Integration).

## Milestone M5: Safe Graph Templates & Minimal Dual Retrieval (PRD §7.3 FR-3.2, §14)

- **Date:** 2026-10-15
- **Objective:** Implement the complete safe parameterized Cypher query template library (7 templates), strict entity resolution policy, index seek plan validation, query safety invariants, and the Minimal Dual Retrieval Engine.
- **Accepted Criteria & Verification:**

| Acceptance Criterion | Requirement | Verification Method | Status |
|---|---|---|---|
| **Safe Template Library** | Minimum 7 templates (`neighbors`, `two_hop`, `path_between`, `shared_neighbors`, `count_by_relation`, `top_connected`, `officers_of`) | `tests/unit/test_graph_templates.py` | **PASS** |
| **Multi-Hop Evidenced Paths** | At least 1 multi-hop query returns correct path with evidence for every edge | `tests/integration/test_m5_minimal_retrieval.py` | **PASS** |
| **Index Seek on Anchor Node** | Query plan verifies `NodeUniqueIndexSeek` on `:Entity(entity_id)` | `EXPLAIN` query plan inspection | **PASS** |
| **Symmetry Invariant** | Symmetric relations (`COMPETES_WITH`, `PARTNERS_WITH`) match undirected | `test_symmetric_relation_undirected_matching` | **PASS** |
| **Directionality Invariant** | Directed relations (`OFFICER_OF`, `SUBSIDIARY_OF`) not matched in reverse | `test_directed_relation_not_matched_in_reverse` | **PASS** |
| **Node Repeat Avoidance** | Intermediate and target nodes cannot repeat within traversal | `test_template_2_two_hop_no_node_repeats` | **PASS** |
| **Hard Caps & Timeouts** | Limit and transaction timeouts enforced at driver level | `test_hard_limit_enforced` & `session.run(..., timeout=5.0)` | **PASS** |
| **Strict Entity Resolution** | Exact/alias resolved, review band flagged as `needs_clarification`, unknown as `not_found`, zero guessing | `test_resolve_entity_strict_*` | **PASS** |
| **Merge History Mapping** | Absorbed entity IDs mapped to surviving canonical node via `entity_merge_history` | `map_to_canonical_entity_id()` | **PASS** |
| **Dual Retrieval Engine** | Unified bundle combining graph paths and vector passages with provenance | `tests/unit/test_retrieval_engine.py` | **PASS** |

- **Test Suite Results:**
  - Full suite: **79/79 passed in 27.88s** (0 failures, 0 regressions).
  - M5 unit tests: 20 passed.
  - M5 integration gate tests: 5 passed.
- **Formal Gate Decision:** **GO (PASSED)**. Milestone M5 complete. Ready to proceed to Milestone M6 (Grounded Answer Generation & Citation Validation).

## Milestone M6: Grounded Answer Generation & Citation Invariants (PRD §7.4, §14)

- **Date:** 2026-10-15
- **Objective:** Implement context assembly (`GRAPH FACTS` [G#] and `RETRIEVED PASSAGES` [P#]), request-scoped `EvidenceRegistry`, grounded prompt generation, mechanical citation resolution validator, feedback retry loops, and out-of-scope refusal logic.
- **Accepted Criteria & Verification:**

| Acceptance Criterion | Requirement | Verification Method | Status |
|---|---|---|---|
| **Graph Path Verbalization** | Convert graph paths into human-readable statements preserving observation IDs & source chunks | `tests/unit/test_verbalizer.py` | **PASS** |
| **Context Assembly & Registry** | Labeled sections `[G#]`, `[P#]`, passage deduplication, token budget enforcement, internal request-scoped registry | `tests/unit/test_context_assembly.py` | **PASS** |
| **Mechanical Citation Resolution** | 100% of citation labels map to a chunk actually retrieved for that request; enforced as runtime invariant | `tests/unit/test_citation_validator.py` | **PASS** |
| **Hallucination Rejection** | Invented citation labels (e.g. `[P99]`) are rejected with targeted regeneration feedback | `test_validate_citations_hallucinated_label_rejected` | **PASS** |
| **No Silent Unresolved Answers** | Invariant: Failed citation resolution never silently returns a confident answer | `test_m6_failed_resolution_never_silent` | **PASS** |
| **Out-of-Scope Refusal** | Missing or unevidenced questions cleanly trigger explicit refusal without guessing | `test_m6_out_of_scope_refusal` | **PASS** |
| **Ambiguity Handling** | Ambiguous entity mentions trigger `needs_clarification` | `GroundedAnswerPipeline.answer_question()` | **PASS** |
| **Grounded Generation Pipeline** | Full pipeline (`answer_question`) generating grounded answers with verified citations | `tests/integration/test_m6_grounded_answer.py` | **PASS** |

- **Test Suite Results:**
  - Full suite: **97/97 passed in 48.94s** (0 failures, 0 regressions).
  - M6 unit tests: 13 passed (`test_verbalizer.py`, `test_context_assembly.py`, `test_citation_validator.py`).
  - M6 integration gate tests: 5 passed (`test_m6_grounded_answer.py`).
- **Formal Gate Decision:** **GO (PASSED)**. Milestone M6 complete. Ready for Milestone M7 (FastAPI Query Endpoints & Baseline Endpoint).
