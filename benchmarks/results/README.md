# Benchmark Results & Historical Artifact Inventory

This directory stores evaluation artifacts generated across development milestones.

## Inventory of Historical Result Artifacts

| Artifact File | Milestone | Date | Questions (N) | Evaluation Scope | Runtime & Models Evaluated | Status |
|---|---|---|---|---|---|---|
| [`retrieval_eval_results.json`](./retrieval_eval_results.json) | **M4** | 2026-10-15 | 40 | Pre-routing dense vector retrieval (Recall@3, @5, @10, MRR) across 6 filers | `nomic-embed-text:768d`, pgvector | **Preserved historical benchmark** |
| [`benchmark_results.json`](./benchmark_results.json) | **M8** | 2026-10-15 | 25 | Comparative end-to-end evaluation: System A (Vector Baseline) vs System C (Hybrid) | Local Ollama `qwen2.5:3b`, `nomic-embed-text:768d`, Neo4j 5.26 | **Preserved historical benchmark** (source of README 25-question figures) |
| [`full_benchmark_results.json`](./full_benchmark_results.json) | **M10** | 2026-10-15 | 2 | 5-way ablation harness test run on TEST split items M10_Q02 & M10_Q03 | Local Ollama `qwen2.5:3b`, `nomic-embed-text:768d` | **Preserved harness test artifact** |
| [`resolution_benchmark.json`](./resolution_benchmark.json) | **M7** | 2026-10-15 | 50 | Entity resolution candidate generation and review-band thresholding | Local embeddings & token overlap | **Preserved historical benchmark** |

---

## Reproducible Run Artifacts (`runs/`)

Every new execution of `python -m kgrag.benchmarks.eval` generates a timestamped, immutable artifact inside `runs/`:
```text
benchmarks/results/runs/benchmark_run_<YYYYMMDD_HHMMSS>_<split>.json
```
This guarantees that rerunning the benchmark produces traceable new records without overwriting or misrepresenting historical runs.

To update the summary report (`docs/full_evaluation_benchmark.md`) and pointer (`full_benchmark_results.json`), supply the `--update-latest` flag.
