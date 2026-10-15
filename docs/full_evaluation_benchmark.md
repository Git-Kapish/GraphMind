# Full 5-Way Ablation Benchmark Report (Milestone M10)

## Executive Summary (PRD §2, §7.5, FR-5.1–FR-5.4)
- **Evaluation Date:** 2026-10-15T16:58:52Z
- **Evaluated Split:** `TEST` (2 hand-verified questions)
- **Target Model:** `qwen2.5:3b` ($0 spend local inference via Ollama)
- **Dense Vector Store:** `chunks (789 rows)` (`nomic-embed-text:768d`)
- **Knowledge Graph Store:** Neo4j 5.26 (331 nodes, 481 relationships)
- **Total Benchmark Runtime:** 14.08s (0.23 min)

## 1. Overall System Performance & Wilson 95% Confidence Intervals

| System ID | System Name | Accuracy | Wilson 95% CI | Citation Resolution | Latency (p50 / p95) |
|---|---|---|---|---|---|
| **A** | System A (Vector Baseline) | **100.0%** (2/2) | [34.2%, 100.0%] | 100.0% | 6096 ms / 6096 ms |
| **C** | System C (Hybrid Auto-Routed) | **100.0%** (2/2) | [34.2%, 100.0%] | 100.0% | 3002 ms / 3002 ms |

## 2. Paired Statistical Comparison: System C (Hybrid) vs System A (Vector Baseline)
- **Measured Accuracy Gap:** **+0.0%**
- **Paired Bootstrap 95% CI (2,000 iterations):** `[0.0%, 0.0%]`
- **Discordant Pairs:** 0 Hybrid Wins vs 0 Baseline Wins (Win Ratio: `0 to 0`)
- **Exact McNemar Two-Sided Test:** p-value = **1.0000**

## 3. Performance by Question Category & Hop Count (PRD §2.2, FR-5.1)

| Category | Sample Size (N) | Evaluation Status | Vector Baseline (A) | Hybrid KG-RAG (C) | Delta (C - A) | Bootstrap 95% CI | McNemar p-value |
|---|---|---|---|---|---|---|---|
| `single_hop` | 2 | [Exploratory: N < 15] | 100.0% | **100.0%** | **+0.0%** | [0.0%, 0.0%] | 1.0000 |

## 4. Failure Taxonomy & Root Cause Analysis (PRD FR-5.2)

| System | Retrieval Miss | Generation / Hallucination | Refusal Error | Router Error | Total Errors |
|---|---|---|---|---|---|
| **A** (System A (Vector Baseline)) | 0 | 0 | 0 | 0 | 0 |
| **C** (System C (Hybrid Auto-Routed)) | 0 | 0 | 0 | 0 | 0 |
