# Benchmark Reproducibility Guide

This report was generated for Run ID `run_20261017_055122` on `2026-10-17T05:51:22.371499+00:00`.

## Cryptographic Dataset Pinning
- **Dataset File:** `eval/datasets/graphmind_eval_v1.jsonl`
- **SHA-256 Checksum:** `a36172b661d1f0691e8f21aff5aca2d43264aa30f14265147b171ea1e1378d2e`
- **Git Commit SHA:** `ba6e25670924da812902bb8bbe663562dab40e39`

## Reproduction Commands
```bash
# 1. Dry-run validation (verifies dataset schema, count, and manifest checksum without model inference)
python -m eval.run_benchmark --mode dry-run

# 2. Full 100-Question comparative evaluation (Vector Baseline vs Hybrid)
python -m eval.run_benchmark --dataset eval/datasets/graphmind_eval_v1.jsonl --mode full --expected-count 100

# 3. Resuming an interrupted evaluation safely without re-evaluating completed questions
python -m eval.run_benchmark --resume --run-id run_20261017_055122
```

## Environment Specifications
- **LLM Target:** `nvidia/nemotron-3.5-super-vl:free (openrouter)`
- **Embeddings:** `nvidia/nemotron-3-embed-1b:free (openrouter)`
- **Decision Logic:** `inception/mercury-decide:free (openrouter)`
