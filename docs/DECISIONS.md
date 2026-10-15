# Architectural & Gate Decisions Log (docs/DECISIONS.md)

| Date | Milestone | Decision | Context & Rationale | Status |
|---|---|---|---|---|
| 2026-10-15 | M0 | Adopt Python 3.12 with uv and Pydantic v2 | Python 3.12 is fully compatible with pgvector, psycopg, neo4j, and edgartools; managed by uv. | Approved |
| 2026-10-15 | M0 | Ollama local runtime with nomic-embed-text & llama3.2 | $0 model spend constraint; local-first; nomic-embed-text matches 768-d pgvector configuration. | Approved |
| 2026-10-15 | M0 | PostgreSQL as authoritative source of truth | Neo4j is a rebuildable projection from extraction_observations. | Approved |
| 2026-10-15 | M2 | Select `qwen2.5:3b` as extraction model | In Model Selection Gate (§6.1), Qwen 2.5 3B achieved 43.55s/chunk vs Llama 3.2 3B at 207.91s/chunk (~4.8x faster on CPU), with 0% timeouts, 100% JSON validity, and 100% quote match. | Approved |
| 2026-10-15 | M2.5 | Go/No-Go Gate: Proceed to M3 (Graph Advantage Confirmed) | In M2.5 Thin Vertical Slice (§0 rule 13, §14), Graph Retrieval scored 10/10 (100%) vs Vector Baseline at 8/10 (80%), retrieving verified multi-hop paths (e.g. Q01: NVIDIA and Microsoft shared market categories) that vector baseline missed. Gate criterion PASSED (GO). | Approved |
| 2026-10-15 | M3 | Entity Resolution & Graph Projection Hardened | Multi-tier candidate resolution (exact -> alias -> token Jaccard -> embedding) benchmarked across 110 hand-verified enterprise pairs with 100% Precision, 100% Recall, 0 False Merges. Rebuild script verified with 100% concordance (267 nodes, 384 edges) and idempotency. | Approved |


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

