# GraphMind Technical Demonstration Walkthrough

**Architecture:** Hybrid Knowledge Graph + Vector RAG over SEC 10-K Filings  
**Target Audience:** Technical Interviewers, AI Engineers, and Evaluators  
**Demo Runner:** [`demo/run_demo.py`](./run_demo.py)  
**Sample Output:** [`demo/sample_output.json`](./sample_output.json)  

---

## 1. Overview & Demonstration Objective

This technical demonstration proves how GraphMind answers complex multi-hop questions over enterprise SEC 10-K filings by combining **graph traversal (Neo4j)** with **dense semantic vector retrieval (pgvector)** and enforcing a **mechanical citation resolution invariant**.

### Representative Benchmark Question
- **Question ID:** `M10_Q31` (from [`benchmarks/questions/benchmark_questions_v2.jsonl`](../benchmarks/questions/benchmark_questions_v2.jsonl))
- **Query:** *"Is Mellanox Technologies connected to NVIDIA, and what is their relationship?"*
- **Category:** `multi_hop` / relational traversal (Hop Count = 2)
- **Filing Sources:** NVIDIA Corporation 10-K (Item 1 Business, Exhibit 21 Subsidiaries)

---

## 2. Quickstart: Running the Demonstration

### Mode A: Instant Deterministic Walkthrough (Zero External Dependencies)
Runs the complete 8-step pipeline using verified execution fixtures and the real Python validation logic. Requires no database or API credentials:

```bash
python -m demo.run_demo --fixture
```

To export the structured execution payload:
```bash
python -m demo.run_demo --fixture --json-out demo/sample_output.json
```

### Mode B: Live End-to-End Execution
Runs against active PostgreSQL (`pgvector`), Neo4j, and live OpenRouter models:

```bash
# 1. Start database services
docker compose up postgres neo4j -d

# 2. Run live demonstration
python -m demo.run_demo --live
```

---

## 3. Step-by-Step Workflow Walkthrough

### Step 1: Query Routing & Intent Classification
GraphMind does not blindly query every store for every question. The router classifies user intent into `vector`, `graph`, or `hybrid`:
- **Model:** Inception Labs `mercury-decide:free` via OpenRouter Decisions API (`POST /api/alpha/decisions`).
- **Calibrated Probabilities:** Evaluates discrete confidence over retrieval paths.
- **Graceful Fallback:** If the decision model encounters rate limits (HTTP 429) or confidence falls below threshold ($< 0.65$), a deterministic rule-based router (entity gazetteer + relational syntax parser) engages with zero downtime.

### Step 2: Dual Evidence Retrieval
- **Store A (Neo4j):** Executes safe Cypher templates to traverse parent-subsidiary relationships:
  $$\text{(Mellanox Technologies)} \xrightarrow{\text{SUBSIDIARY\_OF}} \text{(NVIDIA Corporation)}$$
- **Store B (PostgreSQL + pgvector):** Performs cosine similarity search over 2048-dimensional dense embeddings (`nvidia/nemotron-3-embed-1b:free`, stored in `halfvec(2048)` with HNSW indexes). Retrieves narrative context describing NVIDIA's 2020 acquisition of Mellanox for $6.9 billion.

### Step 3: Request-Scoped Evidence Registry
Retrieved items are isolated in a request-scoped `EvidenceRegistry` and assigned immutable citation labels:
- `[G1]` $\rightarrow$ Graph Fact (Exhibit 21 relationship)
- `[P1]` $\rightarrow$ Passage 1 (Item 1 Business narrative)
- `[P2]` $\rightarrow$ Passage 2 (Exhibit 21 subsidiaries list)

### Step 4: Grounded Generation
The generator (`nvidia/nemotron-3.5-super-vl:free`) synthesizes the answer strictly from the registered evidence and must cite the bracketed labels:
> *"Mellanox Technologies is a wholly owned operating subsidiary of NVIDIA Corporation [G1]. NVIDIA completed its acquisition of Mellanox in April 2020, integrating its InfiniBand and Ethernet networking products into NVIDIA's Data Center business [P1], as documented in NVIDIA's Exhibit 21 subsidiary disclosures [P2]."*

### Step 5: Mechanical Citation Invariant Validation
Unlike heuristic LLM-as-a-judge approaches, GraphMind enforces a **mechanical citation resolution invariant**:
1. Every citation label (`[G#]`, `[P#]`) is parsed via regex.
2. Every label must exist in the request-scoped `EvidenceRegistry`.
3. Every label must resolve to an authoritative chunk retrieved for that specific request.

#### Negative Test Demonstration (Hallucinated Citation Rejection)
To prove the validator is active and cannot be bypassed, the runner injects an intentional test fixture containing an unresolved citation label (`[P99]`):
- **Input:** *"...with additional undisclosed terms documented in confidential contracts [P99]."*
- **Validator Decision:** `REJECTED` (`is_valid = False`, `resolution_rate = 0.67`)
- **Caught Labels:** `['[P99]']`
- **Feedback Loop:** Automatically provides actionable corrective feedback to the generator for regeneration.

### Step 6: System One Claim-Support Verification
Separate from mechanical chunk resolution, `MercuryDecideClient.decide_claim_support()` executes a bounded decision verifying whether the cited passage text semantically substantiates the factual assertion (`supported` vs `unsupported`).

### Step 7: Head-to-Head Baseline Comparison
The same question is executed through the vector-only baseline (`/query/baseline`):

| Evaluation Dimension | System A (Vector Baseline) | System C (Hybrid GraphMind) | Technical Advantage |
|---|---|---|---|
| **Retrieval Mechanism** | Cosine similarity ($k=5$) over chunk embeddings | Graph path traversal + Vector dense search merged via RRF | Graph bridges entity relationships split across disparate filing sections |
| **Citation Invariant** | 92.0% resolution across full benchmark | **100.0% resolution invariant strictly enforced** | Mechanical feedback retry loop eliminates unresolved citations |
| **Multi-Hop Accuracy** | 50.0% (3/6) | **83.3%** (5/6) | **+33.3% accuracy gap** on multi-hop corporate relationship questions |
| **Median Latency** | 11,809 ms | **7,339 ms** | Direct graph traversal circumvents costly token-heavy vector context reranking |

---

## 4. API Testing Commands (HTTP cURL)

If running the live FastAPI server (`uvicorn kgrag.api.app:app --port 8000`):

### 1. Auto-Routed Hybrid Query
```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Is Mellanox Technologies connected to NVIDIA, and what is their relationship?", "mode": "auto"}'
```

### 2. Vector-Only Baseline Query
```bash
curl -s -X POST http://localhost:8000/query/baseline \
  -H "Content-Type: application/json" \
  -d '{"question": "Is Mellanox Technologies connected to NVIDIA, and what is their relationship?"}'
```

### 3. Component Health Reachability
```bash
curl -s http://localhost:8000/health
```

---

## 5. Troubleshooting & Fallback Behaviors

| Issue | Cause | GraphMind Resilience Behavior |
|---|---|---|
| **OpenRouter HTTP 429** | Free-tier rate limits on Mercury Decide | Router immediately engages deterministic fallback (syntax + entity gazetteer); queries do not crash. |
| **Missing Model API Key** | `OPENROUTER_API_KEY` unset or mock key | Router operates in fallback mode; claim-support flags as `not_evaluated`; tests continue deterministically. |
| **Database Container Offline** | Docker daemon stopped or port unavailable | Use `python -m demo.run_demo --fixture` for deterministic offline verification; `tests/conftest.py` skips fixture seeding without timeouts. |
