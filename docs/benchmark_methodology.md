# GraphMind Benchmark Evaluation Methodology & Discrepancy Audit

**Document Version:** 2.0.0  
**Updated:** 2026-10-16  
**Applicable Milestones:** M4, M8, M10, v2.0  

---

## 1. Root Cause Diagnosis of Historical Benchmark Discrepancies

An audit of the evaluation pipeline resolved the discrepancy between the 25-question evaluation reported in [`README.md`](../README.md) and the 2-question report in [`docs/full_evaluation_benchmark.md`](./full_evaluation_benchmark.md):

### A. Origin of the 25-Question Figures (Milestone M8)
- **Source Artifacts:** [`benchmarks/results/benchmark_results.json`](../benchmarks/results/benchmark_results.json) and [`docs/preliminary_benchmark.md`](./preliminary_benchmark.md).
- **Date & Setup:** 2026-10-15; evaluated using local Ollama (`qwen2.5:3b` for LLM generation, `nomic-embed-text:768d` for dense retrieval) against PostgreSQL 17 + pgvector and Neo4j 5.26.
- **Dataset Evaluated:** 25 hand-verified questions (`M8_Q01` through `M8_Q25`) covering:
  - `single_hop`: 6 questions (Baseline 66.7%, Hybrid 83.3%)
  - `two_hop`: 8 questions (Baseline 87.5%, Hybrid 100.0%)
  - `multi_hop`: 6 questions (Baseline 50.0%, Hybrid 83.3%)
  - `out_of_scope`: 5 questions (Baseline 80.0%, Hybrid 80.0%)
  - **Aggregate:** 18/25 (72.0%) Baseline vs 22/25 (88.0%) Hybrid.
- **Discordant Pairs:** 4 Hybrid wins, 0 Baseline wins, 21 ties.
- **Status:** Legitimate empirical exploration from Milestone M8 that served as the primary performance demonstration in the project overview.

### B. Origin of the 2-Question Report (Milestone M10)
- **Source Artifacts:** [`benchmarks/results/full_benchmark_results.json`](../benchmarks/results/full_benchmark_results.json) and [`docs/full_evaluation_benchmark.md`](./full_evaluation_benchmark.md).
- **Date & Setup:** 2026-10-15T16:58:52Z; Milestone M10 introduced the automated 5-way ablation harness (`src/kgrag/benchmarks/eval.py`).
- **Why Only 2 Questions?** During validation of the newly implemented harness, a quick test was executed with `--limit 2` (evaluating only `M10_Q02` and `M10_Q03`).
- **The Defect:** The original `eval.py` script hardcoded the output destination to directly overwrite `full_benchmark_results.json` and `docs/full_evaluation_benchmark.md` on every run. Consequently, that 2-question test obliterated the previous artifact, leaving the repository with a 2-question report showing 100% (2/2) accuracy for both systems while the README displayed the 25-question figures from M8.

### C. Audit of Statistical Significance Claims
- **The Issue:** The README table previously claimed:
  `4 Hybrid wins vs 0 Baseline (p < 0.05)`
- **Mathematical Correction:** In an exact two-sided McNemar test (equivalent to a two-sided binomial test on discordant pairs with $p_0=0.5$):
  $$\text{Two-sided } p = 2 \times \binom{4}{0} \times (0.5)^4 = 2 \times \frac{1}{16} = 0.1250$$
  Because $p = 0.1250 \ge 0.05$, this sample size is **underpowered** to reject the null hypothesis at the $\alpha = 0.05$ level. A minimum of 6 discordant wins with 0 losses is mathematically required to achieve $p < 0.05$ ($2 \times 0.5^6 = 0.03125$).
- **Resolution:** The claim has been reconciled: the win ratio (4 to 0) is reported as an exploratory result with an explicit statistical power caveat.

---

## 2. Benchmark Architecture & Formally Defined Metrics

All metric calculations are implemented as pure, tested functions in [`src/kgrag/benchmarks/metrics.py`](../src/kgrag/benchmarks/metrics.py).

### Metric Definitions & Denominators

| Metric | Mathematical Formula | Denominator Definition |
|---|---|---|
| **Recall@k** | $\frac{1}{N_{\text{answerable}}} \sum_{i=1}^{N_{\text{answerable}}} \mathbb{I}(\text{first\_gold\_rank}_i \le k)$ | Number of answerable queries with non-empty gold chunks. Out-of-scope queries are explicitly excluded from this denominator. |
| **MRR** | $\frac{1}{N_{\text{answerable}}} \sum_{i=1}^{N_{\text{answerable}}} \frac{1}{\text{first\_gold\_rank}_i}$ | Number of answerable queries. Unretrieved items receive reciprocal rank $0.0$. |
| **nDCG@k** | $\frac{1}{N_{\text{answerable}}} \sum_{i=1}^{N_{\text{answerable}}} \frac{\text{DCG}_i@k}{\text{IDCG}_i@k}$ | Normalized discounted cumulative gain with binary relevance at cutoff $k$. |
| **Answer Accuracy** | $\frac{N_{\text{correct}}}{N_{\text{total}}}$ | Total evaluated questions ($N_{\text{total}} = N_{\text{answerable}} + N_{\text{unanswerable}}$). |
| **Citation Resolution Rate** | $\frac{N_{\text{valid\_citations}}}{N_{\text{extracted\_citations}}}$ | Total citation labels extracted from generated answers. Clean refusals (0 citations) vacuously pass (1.0). |
| **Citation Invariant Pass Rate** | $\frac{N_{\text{100\%\_resolved}}}{N_{\text{total}}}$ | Proportion of queries where 100% of produced citations strictly resolve to retrieved evidence chunks. |
| **Refusal Accuracy** | $\frac{N_{\text{correct\_refusals}}}{N_{\text{unanswerable}}}$ | Number of unanswerable / out-of-scope questions. |
| **Latency p50 / p95** | 50th and 95th percentiles of request latency | Total request execution time including routing, retrieval, generation, and validation. |

---

## 3. Dataset Governance (Version 2.0.0)

- **Dataset File:** [`benchmarks/questions/benchmark_questions_v2.jsonl`](../benchmarks/questions/benchmark_questions_v2.jsonl)
- **Metadata Specification:** [`benchmarks/questions/dataset_metadata.json`](../benchmarks/questions/dataset_metadata.json)
- **Split Breakdown:**
  - `dev` (12 questions): For router threshold calibration and prompt refinement.
  - `test` (48 questions): Held-out evaluation split covering `single_hop`, `two_hop`, `multi_hop`, and `out_of_scope`.
- **Ground-Truth Policy:** All gold answers, chunk IDs, and graph relationships were hand-verified directly against source SEC 10-K filings (Items 1, 1A, 7, 8, and Exhibit 21). No ground truth was generated by the model under evaluation.

---

## 4. Statistical Integrity Policy

1. **Wilson Score Intervals:** Single binomial proportions (accuracy, refusal rate, invariant rate) are reported with Wilson 95% confidence intervals to handle small sample sizes responsibly without Gaussian approximations.
2. **Paired Bootstrap:** For paired comparisons between System C and System A evaluated on identical questions, 95% bootstrap intervals are calculated over 2,000 resamples.
3. **Exact McNemar Test:** Discordant pairs ($n_{10}$ system wins vs $n_{01}$ baseline wins) are evaluated using a two-sided exact binomial test.
4. **Sample Size Gating:** If total discordant pairs $< 10$ or $N < 15$, the result is explicitly flagged as `is_underpowered: true` with a clear advisory note.

---

## 5. Reproducing Benchmarks

### Executing the Benchmark
```bash
# Evaluate System A (Vector Baseline) and System C (Hybrid) on the test split
python -m kgrag.benchmarks.eval --systems A,C --split test

# Evaluate full 5-way ablation across all systems
python -m kgrag.benchmarks.eval --systems A,B,C,D,E --split test

# Save run artifact without overwriting latest pointer
python -m kgrag.benchmarks.eval --systems A,C --split test --output-run-dir benchmarks/results/runs
```

Every run outputs a timestamped artifact in `benchmarks/results/runs/` ensuring full reproducibility and historical traceability.

---

## 6. The 100-Question Standardized Benchmark (GraphMind Eval v1.0)

To resolve sample size underpowering and comprehensively test multi-hop reasoning, aggregation synthesis, and refusal grounding, GraphMind Eval v1.0 was established.

### A. Target Distribution & Category Architecture (N=100)

| Category | Count | Reasoning Depth | Purpose & Design Contract |
|---|---|---|---|
| `single_hop` | 20 | 1 retrieval step | Direct factual grounding (executives, founding dates, headquarters, business segments). |
| `two_hop` | 20 | 2 connected facts | Relationship traversals (acquisitions, shared foundries, corporate customer deployments). |
| `three_hop` | 20 | 3 sequential facts | Extended supply chain, multi-step career paths, and multi-entity competitive ecosystems. |
| `aggregation` | 20 | Multi-filer synthesis | Cross-company headcount sums, fabless vs foundry comparisons, TSMC concentration risk. |
| `out_of_scope` | 20 | Refusal / Abstention | Unindexed companies (Tesla, SpaceX, Disney), future projections, confidential credentials. |
| **Total** | **100** | — | **Balanced, versioned, hand-verified SEC 10-K benchmark.** |

### B. Cryptographic Dataset Pinning
- **Primary Path:** `eval/datasets/graphmind_eval_v1.jsonl`
- **Secondary Mirror:** `benchmarks/questions/graphmind_eval_100q_v1.jsonl`
- **Manifest:** `eval/datasets/dataset_manifest.json`
- **Dataset SHA-256 Checksum:** `a36172b661d1f0691e8f21aff5aca2d43264aa30f14265147b171ea1e1378d2e`
- **Corpus Filers Covered:** 10 technology filers (NVDA, AMD, INTC, AAPL, AVGO, MSFT, GOOGL, AMZN, MU, QCOM).

### C. Extended Metric Formulations

In addition to Recall@k and MRR, GraphMind Eval v1 measures:
1. **Evidence Coverage (Multi-Fact Completeness):**
   $$\text{Coverage} = \frac{1}{N_{\text{answerable}}} \sum_{i=1}^{N_{\text{answerable}}} \frac{|G_i \cap R_i@5|}{|G_i|}$$
   where $G_i$ is the set of required gold passages/facts for question $i$, and $R_i@5$ is the top-5 retrieved evidence set. A 3-hop question recovering only 1 of 3 facts scores $33.3\%$, not $100\%$.
2. **Retrieval Failure Rate:** Fraction of answerable queries where zero gold passages appear in top-5 ($|G_i \cap R_i@5| = 0$).
3. **Retrieved Evidence Citation Membership:** Fraction of cited evidence labels resolving to chunks that were actually retrieved for that specific query.
4. **Unsupported Factual Claim Rate:** Proportion of material factual assertions lacking citation support.

### D. Reproduction Commands
```bash
# 1. Dry-run validation (verifies 100 questions, schema, and manifest SHA-256)
python -m eval.run_benchmark --mode dry-run

# 2. Stratified smoke test (evaluates 5 questions, 1 per category, across System A and B)
python -m eval.run_benchmark --mode smoke

# 3. Full 100-Question comparative benchmark
python -m eval.run_benchmark --dataset eval/datasets/graphmind_eval_v1.jsonl --mode full --expected-count 100

# 4. Resume an interrupted run without duplicating completed records
python -m eval.run_benchmark --resume --run-id <run_id>
```

---

## 7. Empirical Findings & Engineering Realities

Evaluating the system on real multi-hop queries revealed several critical engineering insights:

1. **The Graph Traversal Trap:** When the retrieval router selects `graph` based on officer or acquisition keywords, returning a partial or unhelpful graph fact (e.g. Founder instead of CEO) prevents the system from triggering vector fallback if the graph path is non-empty. This starves the generator of rich descriptive text available in vector passages.
2. **Ambiguity Roadblocks:** Entity ambiguity checks (e.g. asking for clarification on "Mellanox Technologies") can stall automated answer generation, whereas dense vector retrieval directly surfaces relevant acquisition chunks without blocking.
3. **Vector Baseline Strengths:** On focused 10-K corpora, dense embeddings (`nomic-embed-text`) provide strong lexical-semantic alignment. Hybrid retrieval only provides an advantage when multi-hop relationships span non-contiguous sections where dense vector search fails to bridge the intermediate hop.

