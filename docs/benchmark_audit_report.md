# GraphMind Benchmark Infrastructure Audit Report (Milestone M10 / 100-Question Protocol)

**Date:** 2026-10-17  
**Repository:** [https://github.com/Git-Kapish/GraphMind](https://github.com/Git-Kapish/GraphMind)  
**Author:** GraphMind Agentic Engineering Team  
**Scope:** Comprehensive audit of existing evaluation datasets, runners, metrics, endpoints, and governance ahead of the 100-question benchmark.

---

## 1. Executive Summary

This audit assesses the state of GraphMind's evaluation pipeline before scaling from historical pilot evaluations (M8: 25 questions, M10: 60 questions) to a definitive, gold-standard **100-Question Paired Benchmark** comparing:
- **System A:** Vector-Only Baseline (`/query/baseline`)
- **System B:** GraphMind Hybrid Auto-Routed KG-RAG (`/query`)

### Key Diagnostic Findings
1. **Root Cause of Historical Overwrites:** Earlier runs using `eval.py --limit 2` directly overwrote `full_benchmark_results.json` and `docs/full_evaluation_benchmark.md` because output target paths were hardcoded and lacked run isolation.
2. **Statistical Underpowering in Historical Claims:** Milestone M8 ($N=25$) claimed $p < 0.05$ with 4 discordant pairs (4 hybrid wins, 0 baseline wins). The exact two-sided McNemar binomial test yields $p = 2 \times (0.5)^4 = 0.1250 \ge 0.05$. At least 6 discordant pairs are mathematically required to establish significance at $\alpha = 0.05$.
3. **Corpus Coverage:** GraphMind's underlying corpus consists of 10 major enterprise tech SEC 10-K filings (NVDA, AMD, MSFT, INTC, AAPL, AMZN, GOOGL, AVGO, MU, QCOM) with 39 extracted filing sections (Items 1, 1A, 7, and Exhibit 21), offering ample empirical depth for single-hop, two-hop, three-hop, and cross-company aggregation questions.
4. **Endpoint Separation:** `/query/baseline` completely disables graph retrieval, isolates dense pgvector search, and generates grounded answers using the identical context assembly, token budgets, and citation validators as `/query`, ensuring an architecturally fair baseline comparison.

---

## 2. Inventory of Historical Benchmark Runs

| Milestone | Artifact Path | Questions ($N$) | Models Evaluated | Accuracy (Baseline vs Hybrid) | Statistical Status |
|---|---|---|---|---|---|
| **M4 (Retrieval)** | `benchmarks/results/retrieval_eval_results.json` | 18 pairs | `nomic-embed-text:768d` | Recall@5: 94.4% | Pilot retrieval calibration |
| **M8 (Pilot QA)** | `benchmarks/results/benchmark_results.json` | 25 questions | Local Ollama `qwen2.5:3b` | 72.0% (18/25) vs 88.0% (22/25) | Exploratory ($p = 0.1250$) |
| **M10 (Smoke)** | `benchmarks/results/full_benchmark_results.json` | 2 questions | `nemotron-3.5-super-vl` | 100.0% (2/2) vs 100.0% (2/2) | Harness sanity test only |
| **M10 v2.0.0** | `benchmarks/questions/benchmark_questions_v2.jsonl` | 60 questions | OpenRouter Nemotron / Mercury | 12 dev, 48 test split | Intermediate protocol |

---

## 3. Component Reusability & Architecture Audit

### Reusable Components
- **`src/kgrag/benchmarks/metrics.py`:** Formally defines mathematical formulas and explicit denominators for Recall@k, MRR, nDCG@k, Answer Accuracy, Citation Resolution Rate, Invariant Pass Rate, and Refusal Accuracy.
- **`src/kgrag/benchmarks/statistics.py`:** Provides exact two-sided McNemar binomial tests, Wilson score intervals, and paired bootstrap resampling (2,000 iterations).
- **`src/kgrag/answer/validator.py`:** Mechanical citation parser and invariant validator strictly checking that all citation labels resolve to items in the request's evidence registry.
- **`src/kgrag/llm/decisions.py`:** System One routing and claim-support verification via Mercury Decide.
- **`src/kgrag/api/app.py`:** Decoupled `/query/baseline` (Vector System A) and `/query` (Hybrid System B) endpoints.

### Identified Gaps to Remediate for 100-Question Protocol
1. **Target Distribution Gap:** Existing `benchmark_questions_v2.jsonl` has 60 questions across 4 categories (`single_hop`, `two_hop`, `multi_hop`, `out_of_scope`). The 100-question specification mandates 5 balanced categories of exactly 20 questions each:
   - `single_hop`: 20 questions
   - `two_hop`: 20 questions
   - `three_hop`: 20 questions (new dedicated category)
   - `aggregation`: 20 questions (new dedicated cross-company / cross-metric category)
   - `out_of_scope`: 20 questions
2. **Immutable Run Storage:** Benchmark runs must be persisted in isolated directories (`eval/results/<run_id>/`) with `manifest.json`, `question_results.jsonl`, `metrics.json`, `comparison.md`, `failures.md`, `reproducibility.md`, and `test_results.txt`.
3. **Execution Safety & Resumption:** The runner must support `--mode full` (strict 100 questions enforcement), `--mode dry-run` (validation without model calls), `--resume` (resuming failed runs without duplicating questions), and spend-limit protection.
4. **Dataset Integrity Manifest:** A cryptographically verified SHA-256 manifest (`dataset_manifest.json`) verifying unique question IDs, category counts, and field completeness.

---

## 4. Corpus Feasibility Audit

The indexed corpus in `data/processed/` was inspected across all 10 filings:
- **NVIDIA Corporation (NVDA, FY2026):** Items 1, 1A, 7, Exhibit 21. Details on GPU architectures (Blackwell, Rubin), DPUs, Mellanox acquisition ($6.9B, 2020), executive officers (Jensen Huang, Colette Kress, Ajay Puri, Debora Shoquist, Timothy Teter), suppliers (TSMC, Samsung, Micron, SK Hynix), and China export control impacts.
- **Advanced Micro Devices (AMD, FY2026):** Items 1, 1A, 7, Exhibit 21. Details on EPYC CPUs, Instinct GPUs, Xilinx acquisition ($49B, 2022), CEO Lisa Su, foundries (TSMC, GlobalFoundries), and competitive positioning.
- **Intel Corporation (INTC, FY2026):** Items 1, 1A, Exhibit 21. Details on x86 architecture, IFS foundry business, Altera FPGA spinout, packaging technologies.
- **Apple Inc. (AAPL, FY2025):** Items 1, 1A, 7, Exhibit 21. Details on Apple Silicon (M-series, A-series), iPhone/Mac segments, supply chain concentration with TSMC, services revenue.
- **Broadcom Inc. (AVGO, FY2025):** Items 1, 1A, 7, Exhibit 21. Details on VMware acquisition ($69B, 2023), Symantec, CA Technologies, networking silicon, ASIC agreements with hyperscalers.
- **Microsoft Corporation (MSFT, FY2026):** Items 1, 1A, 7, Exhibit 21. Details on Azure cloud infrastructure, OpenAI partnership, custom silicon (Maia, Cobalt), Activision Blizzard acquisition ($69B, 2023).
- **Alphabet Inc. (GOOGL, FY2026):** Items 1, 1A, 7, Exhibit 21. Details on Google Cloud, custom TPU accelerators, DeepMind integration, advertising segments.
- **Amazon.com, Inc. (AMZN, FY2026):** Items 1, 1A, 7, Exhibit 21. Details on AWS cloud infrastructure, custom silicon (Trainium, Inferentia, Graviton), Annapurna Labs acquisition.
- **Micron Technology (MU, FY2026):** Items 1, 1A, 7, Exhibit 21. Details on HBM3E memory for AI accelerators, DRAM/NAND fabrication facilities (Boise, Hiroshima, Taichung).
- **Qualcomm Incorporated (QCOM, FY2025):** Items 1, 1A, 7, Exhibit 21. Details on Snapdragon processors, NUVIA acquisition (Oryon CPU architecture), RF front-end, automotive digital chassis.

Conclusion: The corpus contains 100% genuine SEC filing ground truth sufficient to ground all 100 questions without synthetic data generation.
