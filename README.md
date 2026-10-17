# GraphMind
### Hybrid Knowledge Graph + Vector RAG for SEC 10-K Filings

<p align="center">
  <a href="https://github.com/Git-Kapish/GraphMind/actions"><img src="https://github.com/Git-Kapish/GraphMind/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Neo4j-5.26-008CC1?logo=neo4j&logoColor=white" alt="Neo4j" />
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL + pgvector" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT" />
</p>

> **GraphMind is an auditable RAG system for complex company questions.** It combines knowledge-graph traversal in Neo4j with semantic retrieval in PostgreSQL/pgvector, routes each question to a suitable retrieval path, and validates that every returned citation resolves to evidence retrieved for that request.

[Quickstart](#quickstart) · [Evaluation snapshot](#evaluation-snapshot) · [Architecture](#architecture) · [Design trade-offs](#design-trade-offs) · [Evaluation guide](docs/benchmark_methodology.md)

---

## The problem

Vector-only RAG can retrieve text that looks relevant without reliably connecting facts spread across tables, filings, and corporate relationships. Questions such as “Which subsidiaries of a parent company operate in a given jurisdiction?” may require traversing several entities and combining graph relationships with passages from source documents.

GraphMind indexes SEC 10-K filings in two complementary forms:
- **Knowledge graph:** entities and relationships in Neo4j, queried through controlled Cypher templates.
- **Vector index:** text chunks in PostgreSQL/pgvector, retrieved by semantic similarity.

A router selects `vector`, `graph`, or `hybrid`; hybrid retrieval combines ranked results with Reciprocal Rank Fusion (RRF). The final answer is grounded in a request-scoped evidence registry rather than unrestricted model context.

## At a glance

| Capability | Implementation |
|---|---|
| Hybrid retrieval | Query routing across graph traversal and dense vector retrieval |
| Rank fusion | Reciprocal Rank Fusion (RRF) |
| Evidence and citations | Request-scoped `[G#]` graph facts and `[P#]` passage registry with mechanical resolution checks |
| Claim support | Separate model-based supported/unsupported check |
| Resilience | Deterministic router fallback for low-confidence or rate-limited decision calls |
| Input safety | Retrieved filing text treated as untrusted data |
| Baseline | Vector-only comparison endpoint at `POST /query/baseline` |
| Delivery | FastAPI, React, Docker Compose, GitHub Actions |
| Automated checks | Repository currently documents 143 automated tests |

## Evaluation snapshot

The repository contains a **25-question preliminary paired comparison** from milestone M8. It is useful as an exploratory engineering result, not as a conclusive generalization claim.

### End-to-end QA: vector baseline vs. hybrid

| Metric | Vector-only baseline | Hybrid auto-routed |
|---|---:|---:|
| Correct answers | 18/25 (72.0%) | 22/25 (88.0%) |
| Citation resolution rate | 92.0% | 100.0% |
| Median latency (p50) | 11.809 s | 7.339 s |
| p95 latency | 120.313 s | 46.246 s |

**Observed difference:** hybrid answered 4 more questions correctly in this 25-question run. The paired results had 4 hybrid wins, 0 baseline wins, and 21 ties; the exact two-sided McNemar result is **p = 0.125**, so this sample does **not** establish statistical significance at the 0.05 level.

### Where the exploratory results differed

| Question category | N | Vector-only accuracy | Hybrid accuracy |
|---|---:|---:|---:|
| Single-hop | 6 | 66.7% | 83.3% |
| Two-hop traversal | 8 | 87.5% | 100.0% |
| Multi-hop / aggregation | 6 | 50.0% | 83.3% |
| Out-of-scope / refusal | 5 | 80.0% | 80.0% |

These are small category samples and should be interpreted cautiously. The benchmark methodology and historical run provenance are documented in [`docs/benchmark_methodology.md`](docs/benchmark_methodology.md) and [`docs/preliminary_benchmark.md`](docs/preliminary_benchmark.md). The separate M10 report is a **two-question harness smoke run**, not the same evaluation as M8; see [`docs/full_evaluation_benchmark.md`](docs/full_evaluation_benchmark.md).

### Retrieval ablation (historical M4/M10 results)

The repository's README previously showed a retrieval ablation table. Because the recorded reports span distinct milestones and configurations, do not interpret those figures as if they were one single concurrent experiment. Consult the run artifacts and methodology before comparing retrieval-only values.

**Evaluation limitations:** the corpus and held-out question sets are small, model behavior may vary between runs, and the preliminary result does not prove a statistically significant accuracy improvement. Treat the results as a transparent case study of the current prototype, not production-scale evidence.

## Architecture

```mermaid
flowchart TD
    U(["Question"]) --> UI["React dashboard"]
    UI --> API["FastAPI"]
    API --> R["Router and guardrails"]
    R -->|graph or hybrid| G[("Neo4j knowledge graph")]
    R -->|vector or hybrid| V[("PostgreSQL + pgvector")]
    G --> F["Reciprocal Rank Fusion"]
    V --> F
    F --> E["Request-scoped evidence registry"]
    E --> L["Grounded answer generation"]
    L --> C["Citation resolution validator"]
    C --> S["Answer with resolvable citations"]
    S --> UI
    R -. low confidence / 429 .-> RR["Deterministic fallback router"]
    RR --> G
    RR --> V
```

### Request lifecycle

1. **Route:** classify the query as `vector`, `graph`, or `hybrid`. Low-confidence or rate-limited routing can fall back to deterministic rules.
2. **Retrieve:** graph queries use controlled Cypher templates; semantic queries retrieve passages from pgvector; hybrid requests use both.
3. **Fuse and register evidence:** combine ranked results and assign request-local labels to graph facts and passages.
4. **Generate:** produce an answer grounded in the retrieved evidence.
5. **Validate:** mechanically check that citation labels resolve to evidence available in this request. A separate model-based check assesses whether claims are supported by their citations.
6. **Return:** provide the answer, route information, and citation references through the API.

## Demo and reproducibility

No hosted demo or video recording is linked here yet. You can run the application locally and reproduce the documented evaluation instead of relying on screenshots or canned answers.

### Quickstart

Requirements: Docker with Compose, Git, and an OpenRouter API key for model-backed requests.

```bash
git clone https://github.com/Git-Kapish/GraphMind.git
cd GraphMind
cp .env.example .env
# Add OPENROUTER_API_KEY to .env
docker compose up --build -d
```

Services:

| Service | Local URL |
|---|---|
| React dashboard | http://localhost:3000 |
| FastAPI Swagger UI | http://localhost:8000/docs |
| API health check | http://localhost:8000/health |
| Neo4j Browser | http://localhost:7474 |

Ask a question through the API:

```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Who are the executive officers of NVIDIA Corporation?","mode":"auto"}'
```

For a fair manual comparison, submit the same question with `"mode":"vector"` and `"mode":"hybrid"`. For the dedicated vector-only baseline endpoint, use `POST /query/baseline`. Compare actual responses, route, evidence, citation behavior, and latency; model-backed results can vary.

Stop the services:

```bash
docker compose down
```

### Reproduce the benchmark

See [Benchmark methodology and discrepancy audit](docs/benchmark_methodology.md) for dataset governance, metric definitions, limitations, and run commands. The documented commands include:

```bash
# Compare the vector baseline and hybrid system on the held-out test split
python -m kgrag.benchmarks.eval --systems A,C --split test

# Run the full five-system ablation
python -m kgrag.benchmarks.eval --systems A,B,C,D,E --split test

# Keep a timestamped run artifact
python -m kgrag.benchmarks.eval --systems A,C --split test --output-run-dir benchmarks/results/runs
```

Run artifacts and model configuration should accompany any performance claim. Do not interpret the two-question M10 smoke run as the 25-question M8 evaluation.

## Design trade-offs

| Decision | Why | Cost or limitation |
|---|---|---|
| Graph + vector instead of vector-only | Graph traversal can express explicit relationships; vector search handles narrative text | More complex ingestion, entity resolution, and two stores to maintain |
| Route selectively instead of always running both | Avoid unnecessary work for simpler questions | Routing errors and fallback behavior require testing |
| Reciprocal Rank Fusion | Combines differently scored ranked lists without requiring score calibration | Adds retrieval and merge complexity |
| Request-scoped evidence registry | Citations must resolve to retrieved facts/passages | Citation formatting failures may require regeneration |
| Mechanical citation checks plus claim-support evaluation | Citation existence and citation relevance are different properties | Claim-support evaluation adds latency and relies on another model judgment |
| Free-tier model providers | Low-cost experimentation | Rate limits and model availability are external dependencies |

## Tech stack

| Layer | Technology |
|---|---|
| Language / API | Python 3.12, FastAPI |
| Graph database | Neo4j 5.26, APOC |
| Vector database | PostgreSQL + pgvector, HNSW |
| Frontend | React 19, Vite |
| Models | OpenRouter model endpoints documented in source configuration |
| Tests and linting | pytest, Ruff, Oxlint |
| Delivery | Docker, Docker Compose, GitHub Actions |

## Testing and CI

The repository documents these commands:

```bash
pytest -v
python test_e2e.py
ruff check . && ruff format --check .
cd frontend && npm run lint && npm run build
```

The GitHub Actions workflow is at [`.github/workflows/ci.yml`](.github/workflows/ci.yml). It runs backend quality checks, tests against PostgreSQL/pgvector and Neo4j service containers, the frontend production build, and Docker builds. The live end-to-end check requires configured services and model-provider credentials.

## Repository layout

```text
GraphMind/
├── src/kgrag/              # API, retrieval, graph, vector, and benchmark code
├── frontend/               # React + Vite dashboard
├── benchmarks/              # datasets and benchmark artifacts
├── docs/                    # design, benchmark methodology, and reports
├── tests/                   # unit and integration tests
├── .github/workflows/       # CI
├── Dockerfile
├── docker-compose.yml
└── PRD.md
```

## Limitations and next steps

- **Evaluation scale:** the preliminary comparison contains 25 questions; the 48-question held-out split described in the current methodology needs to be run and interpreted with its sample-size caveats before stronger claims are made.
- **Corpus scale:** 789 text chunks and 331 graph entities are suitable for auditing the prototype, but do not establish behavior on a large enterprise corpus.
- **Provider dependence:** the deterministic fallback applies to routing; embedding and generation still depend on upstream model availability.
- **Operational readiness:** authentication and multi-user access controls, larger-corpus ingestion performance, and incremental graph updates remain potential next steps.
- **Latency:** the preliminary p95 values are high for interactive use, despite the lower hybrid p50. Measure and optimize tail latency before positioning this as a production service.

## Author

Built by **Kapish**, final-year Electronics and Communication Engineering student at Delhi Technological University (Class of 2027). [GitHub profile](https://github.com/Git-Kapish).

## License

MIT. See [`LICENSE`](LICENSE).
