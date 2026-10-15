# Architectural & Gate Decisions Log (docs/DECISIONS.md)

| Date | Milestone | Decision | Context & Rationale | Status |
|---|---|---|---|---|
| 2026-10-15 | M0 | Adopt Python 3.12 with uv and Pydantic v2 | Python 3.12 is fully compatible with pgvector, psycopg, neo4j, and edgartools; managed by uv. | Approved |
| 2026-10-15 | M0 | Ollama local runtime with nomic-embed-text & llama3.2 | $0 model spend constraint; local-first; nomic-embed-text matches 768-d pgvector configuration. | Approved |
| 2026-10-15 | M0 | PostgreSQL as authoritative source of truth | Neo4j is a rebuildable projection from extraction_observations. | Approved |
| 2026-10-15 | M2 | Select `qwen2.5:3b` as extraction model | In Model Selection Gate (§6.1), Qwen 2.5 3B achieved 43.55s/chunk vs Llama 3.2 3B at 207.91s/chunk (~4.8x faster on CPU), with 0% timeouts, 100% JSON validity, and 100% quote match. | Approved |

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
