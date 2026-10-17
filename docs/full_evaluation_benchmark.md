# Full 5-Way Ablation Benchmark Report (Milestone M10)

## Executive Summary (PRD §2, §7.5, FR-5.1–FR-5.4)
- **Evaluation Date:** 2026-10-15T16:58:52Z
- **Evaluated Split:** `TEST` (2 hand-verified questions, harness smoke run)
- **Target Model:** `qwen2.5:3b` ($0 spend local inference via Ollama)
- **Dense Vector Store:** `chunks (789 rows)` (`nomic-embed-text:768d`)
- **Knowledge Graph Store:** Neo4j 5.26 (331 nodes, 481 relationships)
- **Total Benchmark Runtime:** 14.08s (0.23 min)
- **Methodology Reference:** See [`docs/benchmark_methodology.md`](./benchmark_methodology.md) for full audit, definitions, and reproduction commands.

> [!NOTE]
> **Audit & Provenance Note:** This document records the Milestone M10 harness validation test run on 2 held-out test items (`M10_Q02` and `M10_Q03`). For the broader 25-question end-to-end evaluation comparing Baseline vs Hybrid KG-RAG across 4 question categories, consult [`benchmarks/results/benchmark_results.json`](../benchmarks/results/benchmark_results.json) and [`docs/preliminary_benchmark.md`](./preliminary_benchmark.md).

---

## 1. Overall System Performance & Wilson 95% Confidence Intervals

| System ID | System Name | Accuracy | Wilson 95% CI | Citation Resolution | Latency (p50 / p95) |
|---|---|---|---|---|---|
| **A** | System A (Vector Baseline) | **100.0%** (2/2) | [34.2%, 100.0%] | 100.0% | 6096 ms / 6096 ms |
| **C** | System C (Hybrid Auto-Routed) | **100.0%** (2/2) | [34.2%, 100.0%] | 100.0% | 3002 ms / 3002 ms |

---

## 2. Paired Statistical Comparison: System C (Hybrid) vs System A (Vector Baseline)
- **Measured Accuracy Gap:** **+0.0%**
- **Paired Bootstrap 95% CI (2,000 iterations):** `[0.0%, 0.0%]`
- **Discordant Pairs:** 0 Hybrid Wins vs 0 Baseline Wins (Win Ratio: `0 to 0`)
- **Exact McNemar Two-Sided Test:** p-value = **1.0000**
- **Statistical Power Caveat:** Sample size (N=2) and discordant pairs (0) is underpowered for significance testing. Results on this split slice are purely exploratory.

---

## 3. Performance by Question Category & Hop Count (PRD §2.2, FR-5.1)

| Category | Sample Size (N) | Evaluation Status | Vector Baseline (A) | Hybrid KG-RAG (C) | Delta (C - A) | Bootstrap 95% CI | McNemar p-value |
|---|---|---|---|---|---|---|---|
| `single_hop` | 2 | [Exploratory: N < 15] | 100.0% | **100.0%** | **+0.0%** | [0.0%, 0.0%] | 1.0000 |

---

## 4. Failure Taxonomy & Root Cause Analysis (PRD FR-5.2)

| System | Retrieval Miss | Generation / Hallucination | Refusal Error | Router Error | Total Errors |
|---|---|---|---|---|---|
| **A** (System A (Vector Baseline)) | 0 | 0 | 0 | 0 | 0 |
| **C** (System C (Hybrid Auto-Routed)) | 0 | 0 | 0 | 0 | 0 |

---

## 5. Comprehensive Historical M8 Baseline Comparison (25 Questions)

For reference, the 25-question hand-verified benchmark recorded in [`benchmarks/results/benchmark_results.json`](../benchmarks/results/benchmark_results.json):

| Category | Questions (N) | Baseline Accuracy | Hybrid Accuracy | Delta | Discordant Wins (Hybrid / Base) |
|---|---|---|---|---|---|
| `multi_hop` / Aggregation | 6 | 50.0% | **83.3%** | **+33.3%** | 2 / 0 |
| `single_hop` Relational | 6 | 66.7% | **83.3%** | **+16.7%** | 1 / 0 |
| `two_hop` Traversal | 8 | 87.5% | **100.0%** | **+12.5%** | 1 / 0 |
| `out_of_scope` (Refusal) | 5 | 80.0% | **80.0%** | +0.0% | 0 / 0 |
| **Total / Overall** | **25** | **72.0%** (18/25) | **88.0%** (22/25) | **+16.0%** | **4 / 0 (p = 0.1250, exploratory)** |
