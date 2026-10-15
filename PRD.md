# PRD: Knowledge Graph RAG for Enterprise Data

## Open-Source, Local-First Implementation (v3)

| Field | Details |
|---|---|
| Status | Draft v3: build-ready. Incorporates the review fixes listed in Appendix A |
| Owner | Project owner |
| Builder | AI coding agent (Claude Code or equivalent) |
| Source brief | BASWE AI: "Build These Six Projects," Project 1 |
| Model-spend constraint | \$0 model spend; use open-source models and free tools only |
| Primary objective | Demonstrate, with a reproducible benchmark, when graph retrieval improves multi-hop question answering over plain vector RAG |
| Timeline (planning estimate) | Release 1 (M0–M8) ≈ 3–4 weeks at 10–12 h/week with the agent writing most code. Release 2 (M9–M12) ≈ 3–4 more weeks, dominated by human labeling (§7.5, FR-5.0) |

------------------------------------------------------------------------

## 0. Instructions for the coding agent

1.  Read §0–§4 and the section map below before writing code. For each
    milestone, read only the sections the map lists. Do not reload the
    whole PRD every session.
2.  At the beginning of each milestone, provide a short implementation
    plan and wait for approval before making large changes. At the end,
    run the milestone acceptance checks and report the actual results.
3.  Never run full-corpus ingestion until the dev-subset quality gates
    and the dry-run estimate (including the chunk budget in §5.7) have
    been shown to the user and approved.
4.  Put model names, embedding dimensions, thresholds, paths, timeouts,
    limits and prompt versions in configuration. Do not hard-code them
    in application logic.
5.  Maintain `docs/FAILURES.md` throughout development. Record what
    failed, why, the attempted fix and the final outcome.
6.  Never commit raw data, model weights, `.env` files, database
    volumes, or generated secrets.
7.  Write tests alongside implementation. Every meaningful module in
    `src/` must have unit tests; each milestone must end with a runnable
    demonstration.
8.  Do not claim a metric has passed unless the relevant test or
    benchmark actually ran. Distinguish target values from measured
    results.
9.  Preserve provenance through every stage: source document → chunk →
    extraction observation → canonical graph relationship → retrieved
    evidence → answer claim.
10. Do not use free hosted inference as a required dependency. The
    default workflow must work locally; free-cloud GPU execution is
    optional.
11. Do not invent corpus facts, benchmark answers, results, or citations
    to make the demo look successful.
12. If a requirement conflicts with another, stop and explain the
    conflict before silently choosing an interpretation.
13. Build the thin vertical slice (M2.5) before hardening components,
    and stop there for a recorded go/no-go decision.
14. Respect the compute budget (§5.7): measure seconds per chunk in the
    dry-run before choosing how many chunks to extract.
15. Prefer deterministic parsers over LLM extraction wherever the source
    is structured (Exhibit 21, executive-officer tables).
16. Request path versus offline: runtime validation is mechanical and
    cheap; LLM-based claim-support checking is an offline evaluation
    (FR-4.4).

### Section map (what to read for each milestone)

| Milestone | Read |
|---|---|
| M0 | §6, §8 (`/health`), §13 |
| M1 | §5, FR-1.2, §9.1 |
| M2 | FR-1.1, FR-1.3, FR-1.6, §5.7, §6.1 |
| M2.5 | §14 (M2.5 row), FR-3.2 (one template), FR-5.1 (question shape) |
| M3 | FR-1.4, FR-1.5, §9 |
| M4 | §7.2 |
| M5 | §7.3 |
| M6 | §7.4 |
| M7 | §8 |
| M8–M10 | §2, §7.5 |
| M11 | §11 |
| M12 | §15 |

------------------------------------------------------------------------

## 1. Problem and goal

### 1.1 Problem

Vector RAG retrieves passages based on semantic similarity. It can
struggle when an answer requires connecting facts spread across
documents, following two- or three-hop relationships, comparing
entities, or aggregating relationships across a corpus.

### 1.2 Goal

Build a hybrid knowledge-graph and vector RAG system over a real,
relationship-rich corpus that:

-   Extracts a constrained knowledge graph in Neo4j and a vector index
    in PostgreSQL/pgvector from the same source chunks.
-   Uses stable chunk IDs to connect graph evidence and source text.
-   Routes questions to graph retrieval, vector retrieval, or both.
-   Returns answers with citations that resolve to retrieved source
    chunks and are evaluated for actual claim support.
-   Supports explicit refusal or clarification when the evidence is
    missing, ambiguous, or insufficient.
-   Is benchmarked against a fair plain vector-RAG baseline, with
    results reported by hop count and failure category.
-   Is reproducible on local, open-source tooling with zero model spend.

**Primary portfolio artifact:** a benchmark table and accuracy-by-hop
chart at the top of the README. The demo supports the evidence; it does
not replace evaluation.

### 1.3 Non-goals

-   No production multi-tenant service, user accounts, or
    role-management system.
-   No paid APIs or paid hosted model services.
-   No fine-tuning.
-   No free-form model-generated Cypher.
-   No elaborate chat UI in the first release.
-   No claims that graph RAG is universally better than vector RAG.
-   No use of automatically generated graph questions as the sole source
    of benchmark questions.

------------------------------------------------------------------------

## 2. Success metrics and evidence standards

Targets below are hypotheses, not promises. Report measured values even
if they miss the targets. Statistical reporting rules are in §2.2.

| Metric | Target / reporting requirement |
|---|---|
| Single-hop accuracy, hybrid vs vector baseline | Report the paired difference with a 95% CI and sample size. Goal: hybrid is not meaningfully worse (CI includes 0 or favors hybrid) |
| Two-hop accuracy gap | Report the paired difference with CI and discordant-pair counts |
| Three-hop and aggregation accuracy gap | Test the hypothesis that the advantage grows with hop count; report per-category paired differences with CIs, not just point estimates |
| Citation resolution (runtime) | 100% of returned citation labels map to a chunk actually retrieved for that request; enforced and tested as an invariant |
| Citation support / claim grounding (offline) | Measure separately from resolution on all or a documented sample of benchmark answers; report unsupported-claim rate |
| Out-of-scope refusal accuracy | Target ≥80%, with counts |
| Extraction precision | Manually audit at least 50 edges in the dev phase and 100 sampled edges for final reporting when corpus size allows |
| Extraction recall | Fully annotate at least 30 chunks; report recall and F1 overall and per relation type. Also report the pre-filter loss (§5.7) |
| Entity resolution | Report precision, recall and F1 on at least 100 labeled candidate pairs, including hard negatives |
| Router | Report accuracy and confusion matrix on at least 60 hand-labeled questions |
| Vector retrieval | Report recall@3, @5 and @10 on at least 40 question-to-gold-chunk examples before router implementation |
| Graph-path correctness | Report the percentage of returned paths whose edges and direction are supported by verified evidence |
| Oracle-graph diagnostic | On at least 20 multi-hop test questions, supply hand-verified gold graph facts instead of the extracted graph to separate extraction/retrieval failures from generation failures (FR-5.2, system E) |
| Latency | Report p50/p95 by retrieval route, hardware, model and corpus size |
| Ingestion effort | Report wall-clock time, seconds per chunk, chunks processed, pre-filter pass rate, tokens processed, cache-hit rate and GPU-hours if applicable |
| Reproducibility | Record software versions, model tags, prompts, configuration and dataset hashes |

### 2.1 Distinguish mechanical invariants from empirical quality

-   **Citation resolution** can be enforced mechanically: a citation
    label must refer to an item in the request's retrieved-evidence
    registry.
-   **Citation support** is an empirical question: the cited passage
    must actually support the claim.
-   **Graph provenance** is a traceability requirement: every
    relationship observation must point to source evidence.
-   **Factual correctness** is measured with gold answers and evidence;
    it cannot be inferred merely because schema validation or citation
    resolution passed.

Because model spend is \$0, report compute cost as wall-clock time,
tokens, hardware and GPU-hours. An optional "equivalent API cost" may be
shown only if it is explicitly labeled hypothetical and calculated from published rates.

### 2.2 Statistical reporting policy

Samples are small: about 100 questions across five categories leaves
roughly 12–20 test questions per category. Therefore:

-   **Paired design.** Systems answer the same questions, so compare per
    question. For each category and overall, report both accuracies with
    Wilson 95% intervals, the paired difference with a paired-bootstrap
    95% CI, and discordant-pair counts (only hybrid correct / only
    baseline correct). Use an exact McNemar test, labeled exploratory
    when a category has fewer than 15 test questions.
-   Provide a per-question win/loss table in the results so readers can
    inspect individual cases.
-   Do not claim that the advantage grows with hop count from point
    estimates alone. Show per-hop paired differences with intervals and
    use wording such as "consistent with" or "inconclusive".
-   Fix the analysis plan and the dev/test split before looking at test
    results. Compute test results once per final configuration.
-   State the number of comparisons made. Do not present p-values as
    confirmatory.

------------------------------------------------------------------------

## 3. Users and question categories

**Primary user:** an analyst asking questions about a body of company
documents.

Question categories:

| Category | Example shape | Preferred path |
|---|---|---|
| Definition / lookup | "What does Company X say about its export-control exposure?" | Vector |
| Single fact | "Who is the CFO of Company X?" | Vector or graph |
| Two-hop | "Which named supplier is connected to a product offered by Company X?" | Graph, if the corpus explicitly supports both edges |
| Three-hop | "Which companies share a verified supplier with a competitor of Company X?" | Graph, only when each hop is evidenced |
| Comparison | "Which regulations do both X and Y explicitly mention?" | Graph + source passages |
| Aggregation | "How many distinct companies in this corpus name Foundry F as a manufacturer?" | Graph |
| Ambiguous entity | "What does Acme do?" when multiple entities match | Clarify; do not guess |
| Out of scope | "What is X's stock price today?" | Refuse |

Several shapes (especially three-hop questions and anything relying on `SUPPLIES_TO`, `COMPETES_WITH` or `PARTNERS_WITH`) may be unsupported by 10-K text; the feasibility gate (§5.3) decides which categories survive. Examples are shapes, not claims about the dataset. Before using any
example in a demo or benchmark, verify that the actual source corpus
supports the complete answer.

------------------------------------------------------------------------

## 4. Architecture

### 4.1 Offline ingestion

``` text
SEC EDGAR
   │
   ▼
Fetch + rate limit + cache
   │
   ▼
Parse / clean / section extraction
   │
   ▼
Section-aware chunks ──────────────────────────────┐
   │                                               │
   ├──► Embeddings ──► PostgreSQL + pgvector       │
   │                                               │
   └──► LLM structured extraction                  │
            │                                      │
            ▼                                      │
       Schema + ontology validation                │
            │                                      │
            ▼                                      │
       Evidence quote verification                 │
            │                                      │
            ▼                                      │
       Extraction observations + cache             │
            │                                      │
            ▼                                      │
       Entity resolution / review queue            │
            │                                      │
            ▼                                      │
       Neo4j graph with provenance ────────────────┘

Shared stable key: chunk_id
Provenance chain: document → chunk → observation → edge → retrieved evidence
```

### 4.2 Query-time flow

``` text
Question
   │
   ▼
Router (graph | vector | hybrid)
   ├──► Vector path: question embedding → pgvector top-k
   │
   └──► Graph path: entity linking → template selection
                    → typed parameters → safe Cypher template
                    → paths + evidence observation IDs
   │
   ▼
Context assembly (GRAPH FACTS / RETRIEVED PASSAGES)
   │
   ▼
Answer generation with short per-request citation labels
   │
   ▼
Citation resolution validator (mechanical, every request)
   │
   ├──► Resolved: return answer
   └──► Unresolved: regenerate with feedback (max 2),
        then refuse or return validation_failed
   │
   ▼
Answer + citations + route + evidence + metrics + structured logs

Offline only (benchmark harness): claim-support / grounding evaluation,
judge scoring, graph-path correctness audit.
```

### 4.3 Key architectural invariants

1.  The same chunk IDs are used across graph provenance and vector
    storage.
2.  Every graph relationship has one or more source observations with
    verified evidence.
3.  A canonical edge may aggregate observations, but must not erase
    their individual source provenance.
4.  The LLM cannot execute arbitrary Cypher or invent relationship
    types.
5.  All claims presented as facts must be tied to evidence from the
    current request.
6.  Retrieved text is untrusted data, never system instructions.
7.  Baseline and hybrid systems use the same held-out questions and
    comparable generation constraints.
8.  Request-path validation is mechanical and cheap. LLM-based
    claim-support checking is an offline evaluation unless explicitly
    enabled (`runtime_support_check`, default off).
9.  PostgreSQL is the source of truth for observations. Neo4j is a
    derived, rebuildable projection of verified, resolved observations.

------------------------------------------------------------------------

## 5. Data and corpus validation

### 5.1 Candidate primary corpus: SEC 10-K filings

SEC filings are public and useful for real-world ingestion. They may
contain relationships involving subsidiaries, acquisitions, executives,
products, markets, regulations and named partners. They do **not**
reliably expose every supplier/customer relationship.

Source entry points:

-   SEC EDGAR: <https://www.sec.gov/edgar>
-   Company ticker map: <https://www.sec.gov/files/company_tickers.json>
-   Submissions endpoint pattern:
    `https://data.sec.gov/submissions/CIK##########.json`
-   Filing documents:
    `https://www.sec.gov/Archives/edgar/data/{cik}/{accession-no-dashes}/{primaryDocument}`

Requirements:

-   Send a descriptive `User-Agent` with project/contact details,
    configured through `SEC_USER_AGENT` in `.env`.
-   Respect SEC rate guidance. Use conservative pacing, local caching,
    retries with backoff and a configurable request-rate limit.
-   Do not assume an API key is required for the cited public endpoints.
-   Use the correct CIK representation for each endpoint: zero-padded
    CIK where required by the submissions endpoint, and the expected CIK
    format in archive paths. Verify URL construction against real
    filings.
-   Store source URLs and accession metadata.
-   Never make a full-corpus run the first ingestion test.

Default fetch/parse helper: `edgartools` (item-level section extraction, filing index, exhibits). `sec-edgar-downloader` or a small `httpx` fetcher is acceptable if it implements the requirements above. Item extraction from filing HTML is brittle: budget time for it in M1 and log parsing failures in `docs/FAILURES.md`. Exhibit 21 is a separate document within the filing; locate it through the filing index, not `primaryDocument`.

### 5.2 Proposed corpus

Default candidate sector: AI / semiconductor / cloud supply chain.
Candidate filers include:

`NVDA, AMD, INTC, MU, AVGO, QCOM, AMAT, LRCX, KLAC, MRVL, TXN, ON, MSFT, GOOGL, AMZN, META, AAPL, TSLA, ORCL, DELL, SMCI, HPE, CSCO, IBM`

This list is a starting point, not a requirement to ingest every ticker.
Confirm that each selected company has suitable filings for the chosen
period.

Per company, target the latest one or two fiscal years of 10-K filings.
Keep relevant sections where available:

-   Item 1: Business
-   Item 1A: Risk Factors
-   Item 7: MD&A
-   Notes relevant to segments, acquisitions, commitments and related
    parties
-   Exhibit 21: Subsidiaries list
-   Executive officer disclosures (frequently an "Information about our Executive Officers" section in Part I; Part III is usually incorporated by reference from the proxy statement, so director data is **not** reliably available from the 10-K)

Skip irrelevant boilerplate, signature pages and exhibit indexes. Retain
document/section boundaries and enough metadata to cite the original
material.

**Known limitation:** 10-Ks may anonymize major customers and omit
supplier names. Expect relationship coverage to vary. Do not treat a
mention of a company as proof of a supplier, partner or competitor
relationship.

### 5.3 Mandatory corpus feasibility gate

Before committing to the full corpus:

1.  Fetch 5–8 companies with one filing each.
2.  Inspect at least 10 representative cleaned chunks and relevant
    structured sections.
3.  Draft 10–15 candidate multi-hop questions from the source text.
4.  Manually verify every hop, answer and supporting chunk for each
    candidate question.
5.  Count the explicit, overlapping relationships available for each
    proposed relation type.
6.  Record counts per gate, missing relation types, parsing problems,
    and rejected questions with reasons in `docs/corpus_feasibility.md`.

**Gate thresholds.** These are initial values. Fix them before running
the gate. Any later change must be logged in `docs/DECISIONS.md` with
the reason; never relax them silently after seeing results.

| Gate | Requirement (feasibility sample: 5–8 filers, one filing each) |
|---|---|
| G1 Parsing | Items 1, 1A, 7 and Exhibit 21 parsed correctly for at least 80% of sample filings (spot-checked) |
| G2 Relation coverage | At least 5 relation types, each with at least 10 human-verified edges (parser-derived edges count) |
| G3 Cross-document connectivity | At least 15 distinct entities appearing in verified edges from at least 2 different filers' documents (needed for shared-neighbor, path and aggregation questions) |
| G4 Multi-hop answerability | At least 8 candidate two-hop and 4 candidate three-hop questions, with every hop, answer and supporting chunk verified. A roughly 5× scale-up (a conservative linear projection, since cross-company links grow faster than linearly) should cover the 25 two-hop and 20 three-hop targets in FR-5.1 |

**Decision rule.**

-   All gates pass: proceed.
-   G1 fails: fix parsing first (`edgartools`, manual fallback for
    failing filings). This is a tooling problem, not a corpus problem.
-   G2–G4 fail: step 1, add Wikipedia articles for the same companies as
    a second document type, tag every observation with its source, and
    re-run the gates. Step 2, if they still fail, either switch the
    primary corpus (§5.5) or narrow the benchmark categories (for
    example, drop three-hop) and say so in the README.
-   Do not manufacture relationships to satisfy a gate.

### 5.4 Dev subset and scale-up

Use only 5–8 companies with one filing each during development. Expand
to approximately 25–40 companies only after the feasibility,
extraction-quality and runtime gates pass. Corpus size is a target to test, not a mandatory count if it adds little verified relational coverage. It is also capped by the chunk budget in §5.7.

### 5.5 Alternative corpora

| Option | Source / use |
|---|---|
| Wikipedia articles about the same companies and people | Additional relationship density; licensing and provenance must be tracked |
| arXiv papers and citation relationships | Alternative corpus for research-paper graphs |
| Enron email corpus | Internal-style, people-centric data; review privacy and research-use notes |
| MuSiQue, 2WikiMultihopQA or HotpotQA | Optional external sanity check for hop-wise behavior, not a substitute for the primary corpus benchmark |

Use one primary corpus for the headline benchmark. Do not mix datasets
in the main results without explicitly reporting dataset-specific
results.

### 5.6 Data handling and provenance

-   Raw HTML and source files live in `data/raw/` and are gitignored.
-   Cleaned text and parsed documents live in `data/processed/` and are
    gitignored unless a small, legally redistributable sample is
    explicitly approved.
-   Store SHA-256 hashes of cleaned document text.
-   Skip unchanged documents based on content hash.
-   Store `source_url`, `accession`, `form_type`, `fiscal_year`,
    `filing_date` and `section_path` on chunks.
-   Keep a reproducible manifest of source documents and hashes.
-   Do not commit full SEC filings or derived datasets by default;
    provide scripts to fetch them.

### 5.7 Compute budget and extraction pre-filter

Rough planning arithmetic (verify with the dry-run): Items 1/1A/7 of one
10-K are typically over a hundred chunks at 600–800 tokens, and 25–40
filers × 1–2 years is several thousand chunks. At even 10–30 seconds per
chunk on CPU that is tens of hours. Therefore:

1.  **Measure first.** The dry-run reports seconds per chunk for each
    configured model on the user's hardware (FR-1.6).
2.  **Chunk budget.** `max_extraction_chunks` is set in configuration.
    Starting guesses, to be replaced by measured values: CPU-only ≈ 800
    (dev corpus only); 8–12 GB GPU or Apple Silicon with 16+ GB ≈ 3,000;
    with optional free-cloud batch GPU ≈ 6,000. Use one filing per
    company by default and add a second year only if budget remains.
3.  **Deterministic first.** Exhibit 21 and tabular officer lists are
    parsed without an LLM (FR-1.3, rule 11).
4.  **Pre-filter.** Send a chunk to the LLM only if (a) it mentions at
    least 2 entities from a gazetteer (filers, tickers and aliases,
    Exhibit 21 names, previously seen entity names) or (b) it contains a
    relation cue (for example supplier, supply, manufactur, foundry,
    fabricat, acquir, competitor, compete, partner, collaborat, invest,
    subsidiar, customer, licens). The cue list lives in
    `config/prefilter.yaml`.
    -   Evaluate it on the fully annotated sample (FR-5.0): it may drop
        at most 5% of gold edges (target). If exceeded, loosen it.
        Report pass rate and edges lost.
    -   Skipped chunks are still embedded and searchable by the vector
        path.
5.  **Cache and resume** (FR-1.3, FR-1.6) so interrupted runs never
    repay compute.

The dry-run approval (§0, rule 3) must show the post-filter chunk count,
estimated hours and the configured budget.

------------------------------------------------------------------------

## 6. Technology stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | `uv`, `ruff`, `pytest`, Pydantic v2 |
| SEC fetch/parse | `edgartools` (default) | Item-level section extraction and exhibit access. Fall back to `httpx` plus a custom parser if needed |
| Local LLM runtime | Ollama | Default local inference; OpenAI-compatible endpoint where supported |
| LLM abstraction | `LLMClient` interface | Allow alternative local runtimes via configuration; no hosted provider required |
| Generator / extractor | Candidate open instruct models such as Qwen2.5-7B-Instruct or Llama-3.1-8B-Instruct | Verify current model availability, licenses and local compatibility; benchmark at least two candidates on the same extraction sample |
| Router | Same model or smaller local instruct model | Must return a validated enum |
| Judge | Different model family where practical, plus human review | Different families reduce one source of bias but do not guarantee impartiality |
| Embeddings | `BAAI/bge-base-en-v1.5` (768 dimensions) by default; smaller model optional | Model and dimension must be configured together |
| Reranker | `BAAI/bge-reranker-base` optional | If enabled, apply equivalent reranking to baseline and hybrid passage retrieval |
| Graph database | Neo4j Community Edition | Docker; note Community Edition access-control limitations |
| Vector database | PostgreSQL + pgvector | HNSW cosine index |
| API | FastAPI + Uvicorn | Typed request/response schemas |
| Structured output | Runtime JSON-schema support where available, then Pydantic validation | Never trust model output without validation |
| Orchestration | Plain Python modules | LangChain optional only where it provides clear value; avoid unnecessary framework lock-in |
| Infra | Docker Compose | Neo4j + PostgreSQL; Ollama may run on host or in a configured container |
| Demo UI | Minimal Streamlit or static HTML page | Stretch goal; not a release-1 blocker |

### 6.1 Model selection gate

Before running extraction over the full dev subset:

-   Choose at least two candidate models that can run under the
    available hardware and licenses.
-   Use the same 30–50 manually reviewable extraction examples for both
    candidates.
-   Measure valid structured-output rate, evidence-quote match rate,
    relation precision and recall on a fully annotated sample (FR-5.0), average processing time and
    failure rate.
-   Record model tags, quantization, prompt version and hardware.
-   Select a model based on measured quality/throughput trade-offs.
-   Do not expand ingestion if the candidate model fails the agreed
    minimum quality threshold. If neither passes, revise the
    ontology/prompt or choose another model and document the result.

The initial threshold should be set after a small calibration sample and
recorded in `config/settings.yaml`; it must not be silently relaxed to
make a model pass.

### 6.2 Hardware guidance

| Tier | Hardware | Expected use |
|---|---|---|
| Minimum | 16 GB RAM, CPU only | Small dev corpus and smaller models; extraction may be slow |
| Recommended | GPU with 8–12 GB VRAM, or Apple Silicon with 16+ GB unified memory | Quantized 7B–8B model, depending on context length and runtime |
| Optional free-cloud acceleration | Kaggle/Colab free GPU quota when available | Batch extraction only; export structured results and load them locally |

Report the actual hardware in the README. Free-cloud quota, availability
and session duration are not guaranteed; local execution remains the
default path.

------------------------------------------------------------------------

## 7. Functional requirements

### 7.1 Phase 1: Ontology and extraction

#### FR-1.1 Fixed ontology

Maintain `config/ontology.yaml`. The LLM must not invent entity or
relationship types.

Entity types:

`Company, Person, Product, Technology, Market, Location, Regulation`

Initial relationship types:

| Relationship | Direction | Notes |
|---|---|---|
| `SUBSIDIARY_OF` | Company → Company | Parse deterministically from Exhibit 21 (no LLM) where available |
| `ACQUIRED` | Acquiring Company → Acquired Company | Optional year and evidence date; preserve historical context |
| `INVESTS_IN` | Company → Company | Require explicit investment evidence |
| `PARTNERS_WITH` | Company ↔ Company | Store a canonical undirected relationship or normalize direction consistently |
| `SUPPLIES_TO` | Supplier Company → Customer Company | Require explicit supplier/customer evidence |
| `MANUFACTURED_BY` | Product or Company → Company | Define the source/target semantics consistently |
| `COMPETES_WITH` | Company ↔ Company | Require explicit evidence; do not infer solely from industry overlap |
| `OFFERS` | Company → Product |  |
| `BUILT_ON` | Product → Technology |  |
| `COMPETES_IN` | Company → Market |  |
| `OPERATES_IN` | Company → Location |  |
| `SUBJECT_TO` | Company → Regulation | Distinguish applicability from a general risk discussion |
| `OFFICER_OF` | Person → Company | Parse tabular executive-officer lists deterministically; LLM otherwise. Optional role and effective period |
| `DIRECTOR_OF` | Person → Company | **Deferred.** Directors are listed in proxy statements (DEF 14A), not reliably in the 10-K. Enable only if proxies are added to the corpus |

**Symmetric relations.** `PARTNERS_WITH` and `COMPETES_WITH` are
symmetric. `ontology.yaml` flags them `symmetric: true`. The graph writer
stores one edge with endpoints ordered by `entity_id`, and templates
match them without regard to direction. Directed relations must match
the direction defined above; reversed-direction extractions are rejected,
or flipped only under an explicit documented rule.

The ontology must also define allowed properties and type constraints
for each relationship. Relation types may not be created dynamically
from LLM output.

Start with high-confidence structured relationships (for example,
subsidiaries and officers) and add weaker or sparser relationship types
only when source coverage and extraction quality justify them.

#### FR-1.2 Chunking

-   Use section-aware splitting, targeting approximately 600–800 tokens
    with approximately 100-token overlap.
-   Do not split mid-table row.
-   Preserve source offsets and section paths where practical.
-   Stable chunk ID: `"{accession}:{item}:{idx:04d}"`.
-   IDs must remain stable across repeat ingestion of unchanged source
    content. If the chunking algorithm or version changes, record that
    version and handle changed chunk IDs explicitly.

#### FR-1.3 Structured extraction

Each chunk is processed through a structured extraction interface.
Example Pydantic schema:

``` python
class ExtractedRelation(BaseModel):
    head_name: str
    head_type: EntityType
    relation: RelationType
    tail_name: str
    tail_type: EntityType
    evidence_quote: str
    confidence: float  # 0..1, model-reported
    role: str | None = None
    year: int | None = None


class ExtractionResult(BaseModel):
    chunk_id: str
    relations: list[ExtractedRelation]
```

Rules:

1.  Include the filer name and explain that "the Company," "we" and
    "our" refer to the filer where appropriate.
2.  Include a small set of few-shot examples drawn from source chunks
    that are not in the final benchmark test set.
3.  Validate with Pydantic and ontology constraints, including allowed
    source/target types and relationship properties.
4.  Retry invalid structured output up to two times with validation
    feedback, then mark the extraction attempt failed and continue the
    ingestion run.
5.  Verify that `evidence_quote` is present in the source chunk using
    exact or documented fuzzy matching. Reject unsupported relations.
6.  Treat model-reported confidence as a feature, not a calibrated
    probability.
7.  Store each extracted relationship as an **observation** with a
    unique observation ID, source chunk ID, quote, extraction model,
    prompt version, timestamp and validation result.
8.  Cache by
    `(chunk_text_sha256, model, prompt_version, ontology_version, extraction_schema_version)`.
9.  Store failure details and allow retrying failed records without
    reprocessing successful unchanged chunks.
10. Resolve "the Company", "we", "our" and similar self-references to the
    filer entity deterministically in code. Reject literal pronoun-like
    names such as "the Company" as entity names.
11. Use deterministic parsers (no LLM) for Exhibit 21 (`SUBSIDIARY_OF`)
    and tabular executive-officer lists (`OFFICER_OF`). They produce
    observations with `extraction_method = 'parser'`, the source row as
    evidence, and the same validation and provenance rules as LLM
    observations.
12. Apply the chunk pre-filter (§5.7) before LLM extraction. Record
    skipped chunks and the reason.

A canonical graph edge may aggregate multiple observations, but each
observation must remain individually traceable.

#### FR-1.4 Entity resolution

1.  Normalize names conservatively: case-fold, normalize whitespace and
    punctuation, and handle legal suffixes without assuming suffix
    removal proves identity.
2.  Generate candidates using entity type, name tokens, aliases and
    context.
3.  Prefer exact canonical/alias matches before embedding similarity.
4.  Use embedding similarity as candidate generation, not as sole proof
    of identity.
5.  Tune thresholds using at least 100 labeled pairs where practical,
    including hard negatives (similar names that refer to different
    entities).
6.  Allow optional LLM adjudication only for a narrow borderline band,
    with evidence shown to the adjudicator.
7.  Ambiguous candidates must be marked `needs_review` rather than
    automatically merged.
8.  Preserve original surface forms, aliases, source observations and a
    merge history.
9.  Choose a canonical name using documented deterministic rules.
10. Generate stable entity IDs. If a canonical name changes, preserve
    identity and update aliases instead of creating a second node.
11. Report precision, recall and F1; separately list false merges and
    missed merges.

#### FR-1.5 Provenance and graph writes

-   Use `MERGE` for idempotent node and relationship writes.
-   Project into Neo4j only observations with `evidence_verified = true`
    whose endpoints are both `resolved`. PostgreSQL is the source of
    truth; provide `python -m kgrag.graph.rebuild` to rebuild Neo4j from
    observations and an integrity check that compares counts.
-   Every graph relationship must link to one or more verified
    observation IDs.
-   Every observation must link to its source `chunk_id`, document,
    evidence quote and extraction version.
-   Preserve distinct observations rather than replacing them with a
    single quote.
-   Maintain confidence/validation metadata per observation; do not
    collapse multiple observations into an unexplained confidence value.
-   Add uniqueness constraints and indexes appropriate to the installed
    Neo4j Community version.
-   Test that re-ingesting unchanged data does not duplicate nodes,
    relationships or observations.
-   Test that a changed document updates or invalidates its dependent
    chunks, observations and graph links correctly.

#### FR-1.6 Dry-run, checkpoints and recovery

`python -m kgrag.ingest --dry-run` must:

-   Sample a configurable number of chunks (default 20).
-   Report estimated total chunks, model calls, tokens, elapsed time,
    cache-hit assumptions and likely bottlenecks.
-   Clearly label extrapolations as estimates.
-   Report measured seconds per chunk for each configured model on this
    hardware, the pre-filter pass rate, and a recommended
    `max_extraction_chunks` (§5.7).
-   Require `--confirm` for full ingestion.
-   Support `--subset`, resume/checkpoint behavior and a failed-record
    retry command.
-   Report progress and allow interrupted runs to resume without
    duplicating committed work.

### 7.2 Phase 2: Vector index

#### FR-2.1 Chunk embeddings

Embed the same chunk records used by extraction into pgvector. Store:

-   `chunk_id`, `doc_id`, `section_path`, `fiscal_year`, `filing_date`
-   `entity_ids[]` when resolved
-   text, token count, source offsets and embedding-model/version
    metadata

#### FR-2.2 Shared identifiers

Provide helpers for both directions:

-   Graph observation/edge → source chunks
-   Chunk → graph neighborhood and observations

A returned graph path must include the observation IDs and source chunk
IDs that support every edge in the path.

#### FR-2.3 Retrieval evaluation before routing

-   Create at least 40 labeled `(question, gold_chunk_ids)` examples. Reuse gold chunks from benchmark dev questions and add synthetic questions generated from sampled chunks. A human verifies every pair (a quick accept/reject pass).
-   Measure recall@3, @5 and @10 before implementing the router.
-   Document the label policy and how multiple valid gold chunks are
    handled.
-   Store results in `docs/retrieval_eval.md`.
-   Do not begin router implementation until this evaluation is
    complete.

#### FR-2.4 Entity embeddings

Embed entity names and aliases for question-to-node linking. Store
model/version and dimension metadata, and rebuild these embeddings when
the embedding model changes.

#### FR-2.5 Embedding migration

The embedding dimension in PostgreSQL schema, model configuration and
vector index must agree. For v1, use one configured embedding
model/dimension per index. Changing model or dimension requires an
explicit migration/rebuild; do not silently write incompatible vectors.
Include a schema check at startup.

### 7.3 Phase 3: Router and retrieval paths

#### FR-3.1 Router

A local model returns a validated object such as:

``` json
{"route": "graph", "confidence": 0.82}
```

Allowed routes: `graph`, `vector`, `hybrid`.

-   Low confidence triggers hybrid retrieval.
-   Invalid output triggers a documented safe fallback.
-   Log the route, confidence, fallback decision, latency and request
    ID.
-   Evaluate on at least 60 hand-labeled questions and report accuracy plus confusion matrix. Router-evaluation questions may be route-label-only (no gold answer needed) and should include all benchmark dev questions.
-   Router confidence must not be presented as calibrated unless
    calibration has been tested.

Routing guidance:

-   Graph: explicit relationship, connection, multi-hop, comparison and
    relationship aggregation questions.
-   Vector: definitions, policy/risk-language lookups and single facts
    best answered from passages.
-   Hybrid: ambiguous routing, low confidence, or cases where a graph
    path needs textual context.

#### FR-3.2 Graph path: templates only

1.  Extract entity mentions from the question using validated structured
    output.
2.  Link exact aliases first, then use similarity-based candidates.
3.  If an entity is missing or ambiguous, return `not_found` or
    `needs_clarification`; never guess.
4.  Select a `template_id` from an enum and provide typed parameters
    only.
5.  Execute pre-written parameterized Cypher in a read transaction with
    a timeout and hard result limit.
6.  Never execute model-generated Cypher or arbitrary query fragments.
7.  Fetch evidence observations and their source chunks for every
    returned edge.
8.  Validate every relationship type and traversal direction against the
    ontology.

Minimum template library (`src/kgrag/graph/templates.py`):

| Template ID | Purpose |
|---|---|
| `neighbors` | Entities linked to X by relation R |
| `two_hop` | X → ? → ? under selected relation types |
| `path_between` | Bounded paths between A and B; maximum three hops |
| `shared_neighbors` | Entities connected to both A and B |
| `count_by_relation` | Count unique entities connected to X via R |
| `top_connected` | Rank entities by degree under a clearly defined relation/counting policy |
| `officers_of` | People with an explicitly evidenced role at a company |

Templates are pre-written Cypher skeletons. At startup a renderer
builds each concrete query from `(template_id, relation types,
directions)` by interpolating **only relation names that exist in
`ontology.yaml`** (a closed enum) and the direction the ontology defines
(symmetric relations use an undirected pattern). Every entity id and
value is a bound parameter. Never interpolate user or model text.

``` cypher
// two_hop rendered for R1 = ACQUIRED, R2 = ACQUIRED (both directed)
MATCH (a:Entity {entity_id: $a_id})-[r1:ACQUIRED]->(m:Entity)-[r2:ACQUIRED]->(b:Entity)
WHERE m.entity_id <> a.entity_id
  AND b.entity_id <> a.entity_id
  AND b.entity_id <> m.entity_id
RETURN a.canonical_name AS a, m.canonical_name AS mid, b.canonical_name AS b,
       r1.observation_ids AS observations1, r2.observation_ids AS observations2
LIMIT $limit

// symmetric relation: undirected pattern
MATCH (a:Entity {entity_id: $a_id})-[r:COMPETES_WITH]-(b:Entity)
RETURN b.canonical_name AS competitor, r.observation_ids AS observations
LIMIT $limit
```

Requirements:

-   Every node carries the shared `:Entity` label with a unique
    `entity_id`, so lookups use the unique index. A test checks the
    query plan (`EXPLAIN`/`PROFILE`) for an index seek on the anchor
    node.
-   Template tests must show that a symmetric relation is found
    regardless of stored endpoint order, a directed relation is not
    matched in reverse, no node repeats within a path, and the result
    limit and timeout are enforced.

Aggregation semantics must be explicit: default to counting **distinct
canonical entities**, not raw edges or observations, unless the question
explicitly asks for the latter.

#### FR-3.3 Vector path

-   Embed the question with the configured model.
-   Retrieve HNSW top-k (default 8).
-   Apply only validated metadata filters.
-   Optional reranking must be configurable and applied comparably to
    the vector baseline.
-   Return chunk IDs, scores and metadata for provenance.

### 7.4 Phase 4: Grounded answer generation

#### FR-4.1 Graph path verbalization

Convert graph paths into readable statements with evidence references,
not raw triples. Every graph fact must preserve its supporting
observation and source chunk mapping.

#### FR-4.2 Context assembly

-   Provide two labeled sections: `GRAPH FACTS` and
    `RETRIEVED PASSAGES`.
-   Deduplicate repeated passage content without dropping provenance.
-   Assign short per-request labels such as `[G1]` and `[P3]`.
-   Maintain an internal request-scoped registry mapping every label to
    the real chunk ID, source metadata and, for graph claims,
    observation IDs.
-   Never allow the model to introduce a citation label that is absent
    from this registry.

#### FR-4.3 Generation

The prompt must require the model to:

-   Answer only from supplied evidence.
-   Cite every factual claim.
-   Distinguish directly stated facts from inferences, and avoid
    unsupported inferences.
-   Say that information is insufficient when evidence is missing or
    contradictory.
-   Treat retrieved passages as untrusted data, not instructions.
-   Avoid using model memory to fill gaps.

#### FR-4.4 Citation resolution (runtime) and claim-support evaluation (offline)

**A. Citation resolution (mechanical invariant, every request)**

-   Parse all citation labels.
-   Confirm that every label exists in the current request's evidence
    registry.
-   Confirm that the mapped chunk ID was actually retrieved for the
    request.
-   Reject labels invented by the model or references to chunks not
    retrieved.
-   Track pre-validation and post-validation resolution rates.
-   If a citation is unresolved, regenerate with the validation feedback
    up to two times. If it still fails, return `validation_failed` or a
    refusal-style response. Never return an unresolved citation.

**B. Citation support / claim grounding (offline evaluation metric)**

-   Not in the default request path: extra LLM calls multiply latency
    on local hardware. The benchmark harness runs it on all or a
    documented sample of benchmark answers. At runtime the API field
    `claim_support_status` is `not_evaluated`.
-   Optional `runtime_support_check` (default off) performs cheap
    deterministic checks only, for example that every graph-derived
    claim cites a graph label whose observations are verified, and that
    lexical overlap between a claim and its cited passage exceeds a
    threshold. Do not describe it as a guarantee.
-   Offline method: split answers into atomic claims, check support with
    deterministic checks where possible and a separate-family local
    judge otherwise, hand-review at least 20% of answers, and report the
    unsupported-claim rate separately from the resolution rate along
    with judge-human agreement.
-   For graph-derived claims, require verified observations for every
    edge in the path and expose the source evidence.
-   A real but irrelevant citation does not pass support evaluation.
-   Do not describe an LLM-based support check as a guarantee of truth.

#### FR-4.5 Refusal and ambiguity

Refuse when retrieval has no relevant evidence, the question is out of
scope, or the evidence does not support an answer. Return
`needs_clarification` when the entity link is ambiguous. Contradictory
sources must be surfaced as a conflict rather than arbitrarily choosing
one.

### 7.5 Phase 5: Benchmark against plain vector RAG

#### FR-5.0 Labeling budget and reuse

Human labeling is the largest cost in Release 2. Plan for it explicitly.

| Artifact | Minimum size | Reuse / cost saving | Rough human time |
|---|---|---|---|
| Benchmark questions | About 100 (80 answerable, 20 out-of-scope); floor 60 | Author from filings and exhibits; verify every hop. Out-of-scope questions are quick | 14–18 h |
| Extraction audit and recall annotation | 100 sampled edges; 30 fully annotated chunks | The 30 annotated chunks also serve model selection, pre-filter evaluation and few-shot examples (never from the test set) | 5–6 h |
| Entity-resolution pairs | 100 | Candidate pairs generated automatically from aliases and embedding neighbors, including hard negatives; human accepts or rejects | 1–2 h |
| Router labels | 60 | All benchmark dev questions plus route-only questions with no gold answer | about 1 h |
| Retrieval gold | 40 | Benchmark dev gold chunks plus human-checked synthetic questions from sampled chunks | 2–3 h |
| Manual answer review | At least 20% of test answers, both systems | Random plus hard cases, one shared rubric | 3–4 h |
| **Total** | | | **≈ 26–34 h** |

These are planning estimates; revise them after M1. If time is short,
cut categories or question count (floor 60) before cutting verification
quality.

#### FR-5.1 Question set and gold evidence

Create about 100 questions (floor 60), stratified as follows. Report
smaller category sizes honestly rather than inventing questions.

| Category | Target count |
|---|---|
| Single-hop | 20 |
| Two-hop | 25 |
| Three-hop | 20 |
| Aggregation | 15 |
| Out-of-scope | 20 |

Each JSONL record should include:

``` json
{
  "id": "q001",
  "question": "...",
  "hop_count": 2,
  "category": "two_hop",
  "gold_answer": "...",
  "gold_chunk_ids": ["..."],
  "gold_entities": ["..."],
  "gold_relationships": ["..."],
  "answerable": true,
  "split": "test",
  "notes": "..."
}
```

Rules:

-   Author questions from source text, filing facts and structured
    exhibits, then manually verify every answer.
-   Do not generate the final question set solely from the extracted
    graph.
-   For multi-hop questions, label the intermediate entities, each
    required relationship, and the source evidence for each hop.
-   Stratified split: about 20% dev and 80% test. Dev questions feed
    router labels, retrieval gold, prompt and threshold tuning. Do not
    tune on the test set.
-   Categories with fewer than 15 test questions are labeled
    exploratory in every table (§2.2).
-   Record questions rejected during corpus feasibility checks and why
    they were rejected.

#### FR-5.2 Systems compared and fairness

| ID | System | Purpose |
|---|---|---|
| A | Vector baseline | Vector top-k only |
| B | Graph-only | Graph path only; refuse if no path |
| C | Hybrid, auto-routed | The product |
| D | Hybrid-always | Both paths on every question; isolates router errors |
| E | Oracle-graph diagnostic (**required**) | On at least 20 multi-hop test questions, hand-verified gold graph facts replace the extracted graph. Separates extraction, resolution and retrieval errors from generation errors |
| F | Vector + query decomposition (stretch) | A stronger multi-hop baseline |

All systems use:

-   The same source corpus and held-out questions.
-   The same embedding model and vector index.
-   The same generator and generation prompt style.
-   The same answerability/refusal policy and citation requirements.
-   The same retrieval top-k and comparable context/token budgets where
    practical.
-   The same optional reranker, if enabled for any system.

The principal difference should be retrieval strategy. Document any
unavoidable differences. Label every incorrect answer from systems A and
C with one failure category (extraction miss, resolution error, linking
error, router error, template gap, retrieval miss, generation error,
gold-label error) in the results.

#### FR-5.3 Scoring

Report at least:

1.  Answer correctness.
2.  Retrieval recall (whether gold evidence entered the context).
3.  Graph-path correctness (every required edge is correct and
    supported).
4.  Citation resolution.
5.  Citation support / claim grounding.
6.  Out-of-scope refusal accuracy.
7.  Entity-linking and router accuracy.
8.  Latency p50/p95 and tokens per query.
9.  Ingestion wall-clock time and cache behavior.
10. Extraction precision and recall, and pre-filter loss.
11. Oracle-graph diagnostic results (system E).

A judge model from a different family may assist with answer scoring,
but this does not guarantee unbiased evaluation. Store the rubric and
scoring rationale. Hand-verify at least 20% of final answers selected
randomly and include difficult cases; report judge-human agreement and
disagreements. Use deterministic exact/entity checks where suitable.

Follow the statistical reporting policy in §2.2 (paired tests, intervals, discordant-pair counts). Report raw counts alongside percentages. Do not overstate a result from a small sample.

#### FR-5.4 Outputs

-   `benchmarks/results/*.json`
-   Auto-generated Markdown table
-   Accuracy-by-hop chart
-   `docs/retrieval_eval.md`
-   `docs/grounding_eval.md`
-   `docs/corpus_feasibility.md`
-   `docs/FAILURES.md`

The headline README table must contain actual measured values and sample
sizes. Never fill missing results with placeholders presented as facts.

------------------------------------------------------------------------

## 8. API specification

``` text
POST /query
{
  "question": "string",
  "mode": "auto" | "vector" | "graph" | "hybrid",
  "top_k": 8,
  "debug": false
}

GET /entities/{entity_id}
GET /chunks/{chunk_id}
GET /health
POST /query/baseline
```

A successful query response should include:

``` json
{
  "answer": "string",
  "citations": [
    {
      "label": "P1",
      "chunk_id": "string",
      "doc": "string",
      "section": "string",
      "snippet": "string",
      "supports_claim": "unknown"
    }
  ],
  "route": {
    "chosen": "hybrid",
    "confidence": 0.0,
    "fallback_used": false
  },
  "graph_paths": [],
  "passages": [],
  "validation": {
    "citation_resolution_passed": true,
    "claim_support_status": "not_evaluated",
    "attempts": 1
  },
  "status": "ok",
  "latency_ms": {
    "route": 0,
    "retrieve": 0,
    "generate": 0,
    "total": 0
  }
}
```

The example is a schema illustration, not an expected benchmark result.
Define strict Pydantic request/response models.

Requirements:

-   Validate `question` length and enforce a configurable maximum.
-   Bound `top_k` to a safe configured range.
-   Use request IDs and structured logs.
-   Configure timeouts for LLM and database calls.
-   Return stable, documented error/status codes for invalid requests,
    missing/ambiguous entities, model unavailability, timeouts and
    validation failures.
-   Every routing decision must be written to `routing_log`.
-   Avoid exposing detailed internal evidence or graph paths by default
    unless `debug` is enabled or the selected response contract requires
    them.
-   `/health` should report component reachability without leaking
    secrets.
-   `/query/baseline` must share the answer schema and evaluation
    conventions.

------------------------------------------------------------------------

## 9. Data models

### 9.1 PostgreSQL

Initial schema concepts:

``` sql
documents(
  doc_id PRIMARY KEY,
  company, ticker, cik, form_type, fiscal_year, filing_date,
  accession, source_url, sha256, ingested_at
);

chunks(
  chunk_id PRIMARY KEY,
  doc_id REFERENCES documents(doc_id),
  section_path, item, text, token_count, char_start, char_end,
  entity_ids text[],
  embedding vector(768),
  embedding_model, chunker_version
);

entities(
  entity_id PRIMARY KEY,
  type, canonical_name, aliases text[],
  name_embedding vector(768), embedding_model
);

extraction_cache(
  chunk_sha256, model, prompt_version, ontology_version,
  schema_version, status, result_json,
  tokens_in, tokens_out, latency_ms, created_at,
  PRIMARY KEY(chunk_sha256, model, prompt_version, ontology_version, schema_version)
);

extraction_observations(
  observation_id PRIMARY KEY,
  chunk_id REFERENCES chunks(chunk_id),
  extraction_method,              -- 'llm' | 'parser'
  head_surface, head_type,        -- as extracted, before resolution
  relation_type,
  tail_surface, tail_type,
  head_entity_id NULL,            -- filled after entity resolution
  tail_entity_id NULL,
  resolution_status,              -- 'pending' | 'resolved' | 'needs_review' | 'unresolvable'
  evidence_quote, evidence_verified,
  model_confidence NULL, role NULL, year NULL,
  validation_result,              -- jsonb: schema, ontology and type checks
  model, prompt_version, ontology_version, schema_version,
  created_at
);

entity_merge_history(
  id PRIMARY KEY,
  source_entity_id, canonical_entity_id,
  decision, method, score, reviewer_note, created_at
);

routing_log(
  id PRIMARY KEY,
  ts, question, route, confidence, fallback_used,
  outcome, latency_ms, request_id
);
```

The SQL is conceptual and must be completed with correct types, indexes,
foreign keys and migration scripts. The embedding dimension must match
configuration. If a different dimension is selected, migrations must be
explicit.

### 9.2 Neo4j

Nodes:

``` text
(:Entity:Company|Person|Product|Technology|Market|Location|Regulation {
  entity_id,          // unique across all labels
  canonical_name,
  aliases: [string],
  type
})

Constraints and indexes:
  CREATE CONSTRAINT FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE
  index on e.canonical_name

Relationship properties:
  observation_ids: [string], n_observations: int, source_docs: [string]
```

Relationships carry canonical relation types and point to observations,
either through observation IDs stored on the edge or through a dedicated
observation model. Preserve observation-level provenance and do not
store only a single source quote for a multi-source relationship.

Chunk text remains in PostgreSQL; Neo4j stores references to
chunk/observation IDs. All graph reads used for answering must be traceable back to source chunks.

**Source of truth.** The PostgreSQL `extraction_observations` table is
authoritative. Neo4j edges and their `observation_ids` are a derived
projection and must be rebuildable from it (FR-1.5).

------------------------------------------------------------------------

## 10. Non-functional requirements

| Area | Requirement |
|---|---|
| Idempotency | Re-ingesting unchanged inputs does not duplicate graph entities, edges, observations or chunks |
| Incremental updates | Changed documents invalidate/rebuild dependent chunks, embeddings and graph observations |
| Reproducibility | Record model tags, prompt/ontology/schema versions, seeds where supported, code version and dataset hashes |
| Observability | Structured logs, per-stage latency, model/token counts and cache-hit rate |
| Performance | Report p50/p95; no unsubstantiated hard target |
| Robustness | Retries with backoff, timeouts, DB reconnects, checkpoints and structured failures |
| Portability | Fresh-clone setup works using documented commands |
| Data integrity | Provenance chain is intact and tested end-to-end |
| Configuration | Models, dimensions, thresholds, paths, limits and timeouts are configurable |
| Testability | Unit, integration, regression and evaluation tests are runnable separately |

------------------------------------------------------------------------

## 11. Security and safety

-   Never execute model-generated Cypher.
-   Use a finite template library, validated relation types, typed
    parameters, read transactions, timeouts and hard limits.
-   Neo4j Community Edition has access-control limitations. Keep the
    database bound to localhost in the local development setup, restrict
    network exposure and never expose database ports publicly by
    default.
-   Treat retrieved text as untrusted data. Instructions embedded in a
    document must not override system or developer instructions.
-   Add prompt-injection regression tests using a harmless test document
    containing instruction-like text.
-   Store secrets in `.env` and provide `.env.example` without secrets.
-   Configure the SEC `User-Agent` via environment.
-   Avoid logging full prompts or sensitive environment values.
-   Public SEC filings are the primary corpus, but data-handling and
    license requirements for any supplementary corpus must be reviewed
    separately.
-   Do not claim that the system is production-secure; this project is a
    local portfolio prototype.

------------------------------------------------------------------------

## 12. Repository layout

``` text
kg-rag/
├── README.md
├── PRD.md
├── CLAUDE.md
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── .env.example
├── config/
│   ├── settings.yaml
│   └── ontology.yaml
├── data/                         # gitignored
│   ├── raw/
│   └── processed/
├── src/kgrag/
│   ├── llm/
│   ├── data/
│   ├── extract/                    # Ex.21/officer parsers, pre-filter, LLM extractor
│   ├── resolve/
│   ├── graph/
│   ├── vector/
│   ├── route/
│   ├── answer/
│   ├── baseline/
│   ├── evaluation/
│   ├── api/
│   └── ingest.py
├── benchmarks/
│   ├── questions/
│   ├── labels/
│   ├── run_benchmark.py
│   └── results/
├── docs/
│   ├── FAILURES.md
│   ├── DECISIONS.md
│   ├── corpus_feasibility.md
│   ├── retrieval_eval.md
│   ├── grounding_eval.md
│   └── architecture.png
└── tests/
    ├── unit/
    ├── integration/
    ├── regression/
    └── evaluation/
```

------------------------------------------------------------------------

## 13. Configuration requirements

`config/settings.yaml` must contain, at minimum:

-   LLM runtime endpoint and model tags.
-   Embedding model and dimension.
-   Optional reranker model and enabled flag.
-   Prompt, ontology, schema, chunker and extraction versions.
-   Extraction confidence floor and evidence-match settings.
-   Entity-resolution thresholds and review band.
-   Router confidence threshold.
-   Query top-k, result limits, context budget and timeouts.
-   SEC request pacing and cache directories.
-   Database connection settings via environment-variable references.
-   Dry-run sample size and full-ingestion confirmation behavior.
-   `max_extraction_chunks`, pre-filter settings (`config/prefilter.yaml`)
    and the pre-filter loss target.
-   `runtime_support_check` flag (default off).
-   Symmetric-relation flags and relation directions (in
    `ontology.yaml`).
-   Statistics settings: bootstrap iterations, random seed, minimum
    category size for non-exploratory reporting.

The application must validate configuration at startup and fail with an
actionable error when incompatible settings are supplied.

------------------------------------------------------------------------

## 14. Milestones and acceptance criteria

Timeline (planning estimate; depends on hardware, model throughput and
corpus quality): Release 1 (M0–M8) takes roughly 3–4 weeks at 10–12
hours per week with the coding agent writing most code. Release 2
(M9–M12) takes roughly 3–4 more weeks and is dominated by human labeling
(FR-5.0).

### Release 1: Prove the core idea

| Milestone | Deliverables | Acceptance criteria |
|---|---|---|
| M0: Scaffold and infra | Repo, Compose, config loader, LLM interface, health endpoint | Fresh setup works; local model returns schema-valid output on a smoke prompt |
| M1: Corpus feasibility + ingestion | SEC fetcher, cache/rate limit, parser (`edgartools`), Exhibit 21 parser, chunker, feasibility report | Dev subset exists; 10 chunks spot-checked; gates G1–G4 (§5.3) evaluated and recorded in `docs/corpus_feasibility.md` |
| M2: Extraction | Ontology, schema, prompts, evidence validation, deterministic parsers, pre-filter, cache, dry-run | Compare two models on the same sample; review at least 50 edges; report structured-output rate, evidence-match rate, recall on annotated chunks, pre-filter loss, and measured seconds per chunk |
| M2.5: Thin vertical slice (go/no-go) | On 5–8 filers: M2 outputs, **naive** resolution (exact normalized-name match), simple graph load, chunk embeddings with pgvector top-k, one or two Cypher templates, and a script (no API) that answers at least 10 hand-verified questions (at least 4 multi-hop) with the vector baseline and with graph retrieval, printing paths and evidence | A written go/no-go note in `docs/DECISIONS.md`: does graph retrieval return correct, evidenced answers that the vector baseline misses on at least one verified multi-hop question? Decision: continue, change corpus (§5.3 fallback), or narrow scope. No statistical claims. Do not start M3 before the note exists |
| M3: Entity resolution + graph | Candidate matching, review queue, merge history, graph writer, rebuild command | Labeled-pair metrics reported; rerun idempotency test passes; Neo4j rebuild from observations matches; source provenance can be traced from sample paths |
| M4: Vector index | Embeddings, pgvector HNSW, entity embeddings, shared-ID helpers | Recall@3/5/10 report exists in `docs/retrieval_eval.md` before M5 starts |
| M5: Minimal retrieval | Safe graph templates (all of FR-3.2) and vector retrieval; no router required yet | At least one verified multi-hop query returns a correct path with evidence for every edge; template tests pass (symmetry, direction, index use); vector retrieval returns source chunks |
| M6: Grounded answers | Context assembly, generation, citation registry and resolution validator | Citation-resolution regression tests pass; failed resolution does not silently return a confident answer |
| M7: API + baseline | FastAPI query endpoints and integration tests | End-to-end answer returns route, status and resolvable citations; baseline endpoint uses matching generation conventions |
| M8: Preliminary comparison | Verified question set of at least 20 questions; offline claim-support harness (sampled) | Compare vector and graph/hybrid results; report failures and limitations without claiming statistical significance |

### Release 2: Credible evaluation and packaging

| Milestone | Deliverables | Acceptance criteria |
|---|---|---|
| M9: Scale ingestion | Dry-run approval (§5.7), expanded corpus within the chunk budget, checkpointed full run | Ingestion time, chunk/edge/observation counts, pre-filter loss and cache metrics recorded; repeat run is idempotent |
| M10: Router + full evaluation | Router, 60+ labeled router questions, about 100 benchmark questions (floor 60), systems A–E, oracle-graph diagnostic | Held-out results by hop count with paired intervals and discordant-pair counts (§2.2), retrieval recall, graph-path correctness, citation support, refusal accuracy and latency reported |
| M11: Robustness | Failure/recovery tests, prompt-injection regression, ambiguity handling | Interrupted ingestion resumes; ambiguous entity does not silently resolve; unsafe query-generation test is blocked |
| M12: Packaging | README, architecture diagram, decision log, failure log, demo script | Fresh-clone setup works; benchmark table contains measured values and sample sizes; no fabricated results |

Do not begin the next milestone until the previous milestone's
acceptance checks are run and the outcome is documented. The agent
should report blockers instead of silently skipping acceptance checks.

------------------------------------------------------------------------

## 15. README and demo requirements

README order:

1.  One-sentence project description and headline measured result.
2.  Benchmark table with sample sizes and accuracy-by-hop chart.
3.  Architecture diagram.
4.  How to reproduce the benchmark.
5.  Two or three real design trade-offs.
6.  What did not work and what was changed.
7.  Hardware, setup and model requirements.
8.  Corpus sources and limitations.
9.  Known failure cases and next steps.

The headline result must be based on the held-out test set. If the
result is inconclusive or hybrid RAG does not outperform the baseline,
say so clearly.

### 90-second demo

1.  Ask a verified multi-hop question.
2.  Show the vector baseline response and its evidence.
3.  Show graph/hybrid retrieval, the traversed path and the supporting
    evidence for every edge.
4.  Open a citation and show the source chunk.
5.  Ask an out-of-scope or unsupported question and demonstrate refusal.
6.  If time permits, show a failure case and explain it.

Resume line template:

> Built a hybrid knowledge-graph and vector RAG system over N filings
> using open-source models; measured multi-hop accuracy of X% versus Y%
> for a vector baseline on Z held-out questions, with citation-grounding
> and latency results reported.

Replace all placeholders with measured values before using the line.

------------------------------------------------------------------------

## 16. Risks and mitigations

| Risk | Mitigation |
|---|---|
| SEC filings contain too few explicit multi-hop relationships | Mandatory feasibility gate; inspect overlap before scaling; revise corpus/category if necessary |
| Small models extract noisy relationships | Constrained output, ontology validation, evidence quotes, manual audits and model-selection gate |
| Extraction is too slow | Dev subset, cache, section filtering, checkpoints and optional free-cloud batch acceleration |
| "The Company" creates junk entities | Include filer context and validate pronoun-like names |
| Entity resolution merges distinct entities | Hard negatives, review queue, conservative merges and merge history |
| Citation exists but does not support claim | Separate resolution and support validation; claim-level evidence checks |
| Graph path contains a bad edge | Verify each edge observation and all path hops against source chunks |
| Router makes wrong choice | Few-shot labels, hybrid fallback, confusion matrix and held-out evaluation |
| Judge model is biased | Different family where practical, rubric, human review and agreement reporting |
| Benchmark leaks into prompt tuning | Dev/test split; lock held-out questions until final evaluation |
| Database/schema configuration mismatch | Startup validation and explicit migrations |
| Interrupted ingestion leaves inconsistent state | Checkpoints, transactional writes, retryable failures and integrity checks |
| Free GPU service is unavailable | Local-first pipeline; hosted GPU remains optional |
| Prompt injection in source documents | Treat retrieved text as data; add regression tests |
| Graph RAG does not outperform baseline | Report result honestly; analyze where it helps and where it adds overhead |
| Extraction compute exceeds available hardware | Chunk budget, pre-filter, deterministic parsers, dry-run measurement, optional free-cloud batch (§5.7) |
| Human labeling exceeds available time | Labeling budget and reuse plan (FR-5.0); cut categories or question count before cutting verification quality |
| Benchmark too small to separate the systems | Paired tests, intervals, exploratory labels for small categories, honest "inconclusive" reporting (§2.2) |
| Undirected relations missed or double-counted by templates | `symmetric` flag in ontology, ordered-endpoint storage, template tests (FR-3.2) |
| Graph and PostgreSQL observation data drift apart | PostgreSQL is the source of truth; graph is a rebuildable projection with an integrity check (FR-1.5) |
| Weak baseline inflates the graph advantage | Oracle-graph diagnostic; stretch vector + query-decomposition baseline (FR-5.2) |
| 10-K HTML item parsing fails | `edgartools` default, gate G1 (§5.3), manual fallback for failing filings |

------------------------------------------------------------------------

## 17. Open questions to resolve before or during M0

1.  What hardware is available (RAM, GPU/VRAM, or Apple Silicon unified
    memory)?
2.  Is the AI/semiconductor/cloud supply chain sector acceptable, or is
    another corpus preferred?
3.  Is API + README + recorded demo sufficient, or is a small UI
    desired?
4.  What local disk space is available for model weights, source data
    and database volumes?

If these are unanswered, use the smallest local-first dev configuration and keep the choices configurable. Question 1 must be answered, or measured by the M2 dry-run, before the full-run chunk budget (§5.7) is chosen.

------------------------------------------------------------------------

## 18. Forward compatibility

-   **Evaluation project:** preserve query logs and benchmark schemas so
    they can be reused for judge calibration.
-   **Red-team project:** keep `answer(question)` behind one service
    function and provide a test-only path for adding a poisoned
    document.
-   **LLM gateway project:** route all model calls through `LLMClient`,
    so a later gateway integration does not require rewriting
    application logic.

------------------------------------------------------------------------

## 19. Stretch goals

Only consider these after the core benchmark and provenance requirements
pass:

-   Incremental graph updates for changed documents.
-   Community detection and corpus-level summaries.
-   Graph visualization in the demo UI.
-   Supplementary Wikipedia corpus with separately reported results.
-   Quantized-model comparison for extraction quality versus speed.
-   Reranker comparison.
-   External multi-hop dataset as a separate sanity check.

------------------------------------------------------------------------

## 20. Definition of done

The project is complete only when:

-   A fresh clone can start the local stack using documented commands.
-   The dev and selected full corpus are reproducibly fetchable or
    rebuildable.
-   Ingestion is resumable and idempotent.
-   Every graph relationship used in an answer can be traced through a
    verified observation to a source chunk.
-   The vector baseline and hybrid system run on the same held-out
    questions.
-   Results report sample sizes, accuracy by hop count, retrieval
    recall, graph-path correctness, citation resolution, claim support,
    refusal accuracy and latency.
-   At least 20% of benchmark answers are manually reviewed, with
    judge-human agreement reported if a judge is used.
-   Results use the paired reporting policy in §2.2, with categories
    under 15 test questions labeled exploratory.
-   The oracle-graph diagnostic (system E) is reported.
-   Failure cases, limitations and design trade-offs are documented.
-   README results are measured, reproducible and not fabricated.
-   No paid model API is required to run the core project.

------------------------------------------------------------------------

## Appendix A: Changes from v2

| # | Review issue | Resolution | Where |
|---|---|---|---|
| 1 | Feasibility gate had no numbers | Numeric gates G1–G4 and a pre-decided fallback (add Wikipedia, then switch corpus or narrow scope) | §5.3 |
| 2 | Claim-support check sat in the request path | Runtime is mechanical only; claim support is an offline metric; optional cheap check behind a flag | §4.2, §4.3, FR-4.4 |
| 3 | Observation schema did not fit pipeline order | Surface names and types, nullable resolved ids, resolution status, validation result and versions; Postgres is source of truth | §9.1, §9.2, FR-1.5 |
| 4 | No compute budget | Chunk budget, deterministic parsers, pre-filter with a loss target, dry-run measurement | §5.7, FR-1.3, FR-1.6 |
| 5 | Cypher templates unlabeled, directional only, inconsistent on relation types | Shared `:Entity` label, symmetric relations, closed-enum rendering, plan and symmetry tests | FR-1.1, FR-3.2, §9.2 |
| 6 | `DIRECTOR_OF`, Exhibit 21 and HTML parsing realities | `DIRECTOR_OF` deferred; Exhibit 21 via filing index; `edgartools` default | §5.1, §5.2, FR-1.1 |
| 7 | Underpowered statistics | About 100 questions, paired tests, intervals, exploratory labels, ±3 pp parity target replaced | §2, §2.2, FR-5.1 |
| 8 | Labeling load | Explicit labeling budget with reuse | FR-5.0 |
| 9 | Extraction measured on precision only | Recall and F1 on annotated chunks; pre-filter loss | §2, §6.1, §5.7 |
| 10 | Weak baseline | Systems A–F; oracle-graph diagnostic required | FR-5.2 |
| 11 | First end-to-end result came at M8 | Thin vertical slice with go/no-go at M2.5 | §14 |
| 12 | PRD too long to reload each session | Section map in §0, plus a short `CLAUDE.md` | §0 |
