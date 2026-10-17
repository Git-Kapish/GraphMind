"""CLI Bridge to eval.run_benchmark (PRD §2, Milestone M10)."""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.run_benchmark import main, run_benchmark_suite  # noqa: E402

__all__ = ["main", "run_benchmark_suite"]


if __name__ == "__main__":
    main()
