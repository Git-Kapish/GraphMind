# GraphMind — Enterprise Knowledge Graph & Vector RAG

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector_16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Neo4j-5.26_APOC-008CC1?style=for-the-badge&logo=neo4j&logoColor=white" alt="Neo4j" />
  <img src="https://img.shields.io/badge/React-19_Vite-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/OpenRouter-Free_Tier_$0.00-7C3AED?style=for-the-badge" alt="OpenRouter Free Tier" />
  <img src="https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions" />
</p>

> **Hybrid Knowledge Graph & Dense Vector RAG over enterprise SEC 10-K filings with verifiable citation provenance and zero model inference cost ($0.00).**

GraphMind combines structured graph traversals (Neo4j Cypher) with dense 2048-dimensional semantic search (PostgreSQL pgvector) to answer complex multi-hop financial inquiries, subsidiary networks, and executive structures with 100% mechanical citation resolution back to authoritative SEC filings.

---

## 1. System Architecture

```mermaid
flowchart TD
    User([User Query / Analyst]) --> UI[React 19 Dashboard :3000 / :80]
    UI --> API[FastAPI Application :8000]
    
    subgraph "Decision & Routing Layer"
        API --> Router[Query Router & Guardrails]
        Router -.->|Probabilistic Categorization| Mercury[inception/mercury-decide:free]
        Router -->|Deterministic Fallback| RuleRouter[Syntax & Gazetteer Router]
    end

    subgraph "Hybrid Retrieval Layer"
        Router -->|Relational Queries| Neo4j[(Neo4j Graph Database :7687\n331 Entities | 481 Edges)]
        Router -->|Narrative & Risks| PgVector[(PostgreSQL 16 + pgvector :5432\n789 Chunks | 2048-d halfvec)]
        Router -->|Complex Queries| RRF[Reciprocal Rank Fusion RRF]
        Neo4j --> RRF
        PgVector --> RRF
    end

    subgraph "Grounded Synthesis & Validation"
        RRF --> Context[Evidence Registry\n[G1..n] Graph Facts | [P1..n] Passages]
        Context --> LLM[nvidia/nemotron-3.5-super-vl:free\nStrictly Grounded Generation]
        LLM --> Validator[Mechanical Citation Validator]
        Validator -.->|Verify Claim Support| MercuryClaim[inception/mercury-decide:free]
        Validator --> Answer[Audited Response with Verified Citations]
    end

    Answer --> API
```

---

## 2. Multi-Model OpenRouter Architecture

GraphMind enforces a **strict separation of concerns** across three dedicated open-access models on OpenRouter:

| Role | Model Identifier | Endpoint | Representation | Responsibility |
|---|---|---|---|---|
| **System One Decision** | `inception/mercury-decide:free` | `POST /api/alpha/decisions` | Calibrated Probabilities | Query routing (`vector`, `graph`, `hybrid`) and post-generation claim-support verification (`supported`, `unsupported`). |
| **Dense Embeddings** | `nvidia/nemotron-3-embed-1b:free` | `POST /api/v1/embeddings` | `2048-d` float vectors | Text-to-vector projection for document chunks and canonical entity representations with in-memory caching. |
| **Generative LLM** | `nvidia/nemotron-3.5-super-vl:free` | `POST /api/v1/chat/completions` | Natural Language & JSON | Grounded answer synthesis, citation invariant enforcement (`[P1]`, `[G1]`), and structured relation extraction. |

### Architectural Guardrails
- **Zero Hallucinated Citations:** Every bracketed citation (`[P1]`, `[G2]`) must mechanically resolve to an authoritative chunk in the request-scoped `EvidenceRegistry`. Unresolvable citations trigger automatic feedback retry loops.
- **Router Resilience:** If `inception/mercury-decide:free` encounters an upstream rate limit (HTTP 429) or low confidence, the query engine automatically activates rule-based routing with zero query disruption.
- **Untrusted Document Isolation:** Filing texts are treated strictly as passive data; embedded prompt injections or system override attempts are neutralized prior to context assembly.

---

## 3. Quickstart with Docker Compose (Recommended)

Run the entire full-stack application (PostgreSQL + pgvector, Neo4j, FastAPI Backend, and React 19 Frontend) with a single command:

```bash
# 1. Clone repository
git clone https://github.com/Git-Kapish/GraphMind.git
cd GraphMind

# 2. Configure environment variables
cp .env.example .env
# Edit .env and insert your OPENROUTER_API_KEY

# 3. Build and launch all containerized services
docker compose up --build -d
```

### Container Endpoints:
- **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
- **FastAPI API & Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **Neo4j Browser:** [http://localhost:7474](http://localhost:7474) (User: `neo4j`, Password: in `.env`)

To tear down services:
```bash
docker compose down
```

---

## 4. Local Development Setup

### 1. Python Environment

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # On Linux/macOS: source .venv/bin/activate

# Install dependencies in editable mode with development tools
pip install -e ".[dev]"
```

### 2. Databases (Postgres & Neo4j)

Ensure local instances or containerized databases are running:
```powershell
docker compose up postgres neo4j -d
```

### 3. Vector Dimension Migration (768-d to 2048-d)

If updating an existing database to `nvidia/nemotron-3-embed-1b:free`:
```powershell
# Run the pgvector column migration and build halfvec(2048) HNSW indexes
.venv\Scripts\python.exe -c "from kgrag.vector.embeddings import migrate_vector_dimensions; print(migrate_vector_dimensions(target_dim=2048))"

# Re-embed unindexed chunks and canonical entities
.venv\Scripts\python.exe -c "from kgrag.vector.embeddings import embed_unindexed_chunks; print(embed_unindexed_chunks(batch_size=16))"
.venv\Scripts\python.exe -c "from kgrag.resolve.resolver import embed_unembedded_entities; print(embed_unembedded_entities(batch_size=32))"
```

### 4. Running the Backend & Frontend

**Backend Server:**
```powershell
.venv\Scripts\uvicorn.exe kgrag.api.app:app --host 127.0.0.1 --port 8000 --reload
```

**Frontend Client:**
```powershell
cd frontend
npm install
npm run dev
```

---

## 5. Testing & Code Quality

### Automated Test Suite (143 Tests)
```powershell
# Run full test suite
.venv\Scripts\pytest.exe -v

# Run only OpenRouter tests
.venv\Scripts\pytest.exe tests/unit/test_openrouter.py -v
```

### End-to-End Live Verification
Verify configuration, live database vector dimensions, live OpenRouter endpoints, and full RAG queries:
```powershell
.venv\Scripts\python.exe test_e2e.py
```

### Code Formatting & Static Analysis
```powershell
# Backend (Python / Ruff)
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .

# Frontend (React / Oxlint)
cd frontend
npm run lint
npm run build
```

---

## 6. CI/CD Pipeline

The project features a complete GitHub Actions workflow configured at [`.github/workflows/ci.yml`](file:///.github/workflows/ci.yml):

- **Backend Linting:** Enforces strict Ruff lint rules and formatting standards.
- **Frontend Linting:** Validates JSX components with Oxlint.
- **Automated Testing:** Spins up live PostgreSQL + pgvector and Neo4j test services and executes the complete test suite.
- **Frontend Compilation:** Tests Vite production bundle building.
- **Container Verification:** Tests Docker multi-stage builds for both `kgrag-api` and `kgrag-frontend` images.

---

## 7. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Validates reachability of Postgres, Neo4j, and OpenRouter without leaking credentials. |
| `POST` | `/query` | Executes auto-routed or mode-specified (`vector`, `graph`, `hybrid`) RAG query answering. |
| `POST` | `/query/baseline` | Vector-only baseline query endpoint for A/B ablation comparisons. |
| `GET` | `/entities/{entity_id}` | Retrieves canonical entity metadata, degree, and verified graph relationships. |
| `GET` | `/chunks/{chunk_id}` | Retrieves authoritative chunk text, filing section metadata, and extraction observations. |
| `GET` | `/benchmarks/retrieval` | Returns latest 5-way retrieval ablation benchmark metrics and statistical test results. |

---

## 8. License

Distributed under the MIT License. See `LICENSE` for details.
