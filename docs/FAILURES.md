# Failure Log (docs/FAILURES.md)

Record of encountered failures, root causes, attempted fixes, and final outcomes.

| Timestamp | Component / Milestone | Failure Description | Root Cause | Attempted Fix | Final Outcome |
|---|---|---|---|---|---|
| 2026-10-15 | System Init | Missing nvidia-smi | Host has integrated Intel Iris Xe graphics (CPU-only execution) | Configure local LLM client for CPU-optimized models (3B / quantized) and dry-run compute budget | Solved: System operating in local CPU tier per PRD §6.2 |
| 2026-10-15 | M0: Scaffold | Hatchling build failed on `uv pip install -e .` | `README.md` specified in `pyproject.toml` did not yet exist on disk | Created initial `README.md` | Solved: Package and dependencies installed cleanly |
