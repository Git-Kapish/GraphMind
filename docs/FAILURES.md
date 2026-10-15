# Failure Log (docs/FAILURES.md)

Record of encountered failures, root causes, attempted fixes, and final outcomes.

| Timestamp | Component / Milestone | Failure Description | Root Cause | Attempted Fix | Final Outcome |
|---|---|---|---|---|---|
| 2026-10-15 | System Init | Missing nvidia-smi | Host has integrated Intel Iris Xe graphics (CPU-only execution) | Configure local LLM client for CPU-optimized models (3B / quantized) and dry-run compute budget | Solved: System operating in local CPU tier per PRD §6.2 |
| 2026-10-15 | M0: Scaffold | Hatchling build failed on `uv pip install -e .` | `README.md` specified in `pyproject.toml` did not yet exist on disk | Created initial `README.md` | Solved: Package and dependencies installed cleanly |
| 2026-10-15 | M1: Feasibility | Foreign key constraint on `extraction_observations.chunk_id` | Exhibit 21 parser observations pointed to an unpersisted chunk ID | Created structured Exhibit 21 chunk in `chunks` table before inserting observations | Solved: Full relational provenance preserved |
| 2026-10-15 | M2: Model Selection | Llama 3.2 3B timed out on SEC 10-K Item 1 chunks at 90s/240s | Dense ~850-token SEC text caused Llama 3.2 to run repetitive generation loops on CPU, taking >240s | Benchmark Qwen 2.5 3B head-to-head; switch extraction model to Qwen 2.5 3B (43.55s, 0 timeouts) | Solved: Qwen 2.5 3B selected with 120s timeout |
