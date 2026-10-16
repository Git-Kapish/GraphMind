"""Statistical Reporting Engine adhering to PRD §2.2 policy.

Implements:
- Wilson 95% confidence intervals for single binomial proportions.
- Paired bootstrap 95% confidence intervals for paired accuracy differences.
- Discordant-pair analysis (n10, n01, n11, n00).
- Exact two-sided McNemar test for paired binary outcomes.
"""

import math
from typing import Any

import numpy as np
from scipy.stats import binomtest


def wilson_ci(k: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Compute Wilson score interval for a binomial proportion (PRD §2.2)."""
    if n <= 0:
        return (0.0, 0.0)

    p = k / n
    # z-value for 95% confidence (1.95996)
    z = 1.959963984540054
    z2 = z * z

    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half_width = (z * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n)))) / denom

    lower = max(0.0, center - half_width)
    upper = min(1.0, center + half_width)
    return (lower, upper)


def paired_bootstrap_ci(
    y_test: list[bool],
    y_baseline: list[bool],
    n_bootstrap: int = 2000,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Compute paired-bootstrap 95% confidence interval for mean difference (PRD §2.2).

    Returns:
        (mean_diff, ci_lower, ci_upper)
    """
    if len(y_test) != len(y_baseline) or len(y_test) == 0:
        return (0.0, 0.0, 0.0)

    n = len(y_test)
    d = np.array(y_test, dtype=float) - np.array(y_baseline, dtype=float)
    mean_diff = float(np.mean(d))

    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_bootstrap, dtype=float)

    for i in range(n_bootstrap):
        sample_indices = rng.integers(0, n, size=n)
        boot_means[i] = np.mean(d[sample_indices])

    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))
    return (mean_diff, ci_lower, ci_upper)


def mcnemar_exact_test(y_system: list[bool], y_baseline: list[bool]) -> dict[str, Any]:
    """Perform exact McNemar test and discordant-pair accounting (PRD §2.2)."""
    if len(y_system) != len(y_baseline):
        raise ValueError("Input lengths must match for paired McNemar test.")

    n10 = 0  # System correct, Baseline incorrect (System wins)
    n01 = 0  # Baseline correct, System incorrect (Baseline wins)
    n11 = 0  # Both correct
    n00 = 0  # Both incorrect

    for s, b in zip(y_system, y_baseline):
        if s and not b:
            n10 += 1
        elif not s and b:
            n01 += 1
        elif s and b:
            n11 += 1
        else:
            n00 += 1

    discordant_total = n10 + n01
    if discordant_total == 0:
        p_val = 1.0
    else:
        # Two-sided exact binomial test on discordant pairs
        res = binomtest(min(n10, n01), discordant_total, 0.5, alternative="two-sided")
        p_val = float(res.pvalue)

    return {
        "n10_system_wins": n10,
        "n01_baseline_wins": n01,
        "n11_both_correct": n11,
        "n00_both_incorrect": n00,
        "discordant_total": discordant_total,
        "p_value": p_val,
        "system_win_ratio": f"{n10} to {n01}",
    }
