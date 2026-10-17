# GraphMind 100-Question Benchmark Evaluation Report

**Run ID:** `run_20261017_055122` | **Status:** `COMPLETE` | **Git SHA:** `ba6e2567`
- **Dataset:** `graphmind_eval_v1.jsonl` (SHA-256: `d19fa5f4d0cfc4e9...`)
- **Evaluated Questions:** 5 (Balanced 20 per category across 10 SEC filers)
- **Completed Evaluations:** 10 total system-question runs
- **Total Benchmark Runtime:** 145.76s

## 1. Primary Accuracy & Retrieval Metrics Summary

| System | Accuracy (Count) | Wilson 95% CI | Recall@5 | MRR | Evidence Coverage | Citation Resolution | Latency (p50 / p95) |
|---|---|---|---|---|---|---|---|
| System A (Vector Baseline) | **100.0%** (5/5) | [56.5%, 100.0%] | 25.0% | 0.250 | 25.0% | 100.0% | 10674ms / 55839ms |
| System B (GraphMind Hybrid) | **40.0%** (2/5) | [11.8%, 76.9%] | 0.0% | 0.000 | 0.0% | 100.0% | 6898ms / 10501ms |

## 2. Paired Statistical Rigor (N=100 Paired Questions)
- **Measured Accuracy Gap:** **-60.0%**
- **Paired Bootstrap 95% Confidence Interval (2,000 resamples):** `[-100.0%, -20.0%]`
- **Discordant Pairs:** 0 Hybrid Wins vs 3 Baseline Wins (Discordant Total: 3)
- **Exact Two-Sided McNemar Test:** p-value = **0.2500**
- **Statistical Conclusion:** Exploratory difference; cannot conclude statistical significance.

## 3. Accuracy by Question Category (N=20 per category)

| Category | Single-Hop (20) | Two-Hop (20) | Three-Hop (20) | Aggregation (20) | Out-of-Scope (20) |
|---|---|---|---|---|---|
| **System A (Vector Baseline)** | 1/1 (100.0%) | 1/1 (100.0%) | 1/1 (100.0%) | 1/1 (100.0%) | 1/1 (100.0%) |
| **System B (GraphMind Hybrid)** | 0/1 (0.0%) | 0/1 (0.0%) | 0/1 (0.0%) | 1/1 (100.0%) | 1/1 (100.0%) |

## 4. Accuracy by Reasoning Hop Count

| Reasoning Depth | Vector Baseline (A) | GraphMind Hybrid (B) | Delta (B - A) |
|---|---|---|---|
| **1-Hop Reasoning (N=20)** | 100.0% | **0.0%** | **-100.0%** |
| **2-Hop Reasoning (N=20)** | 100.0% | **0.0%** | **-100.0%** |
| **3-Hop Reasoning (N=20)** | 100.0% | **0.0%** | **-100.0%** |
