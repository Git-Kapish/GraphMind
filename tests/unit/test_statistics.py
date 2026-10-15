"""Unit tests for Statistical Reporting Engine (PRD §2.2)."""

import pytest
from kgrag.benchmarks.statistics import (
    mcnemar_exact_test,
    paired_bootstrap_ci,
    wilson_ci,
)


def test_wilson_ci():
    # 0 out of 10
    lower, upper = wilson_ci(0, 10)
    assert lower == 0.0
    assert 0.25 < upper < 0.35

    # 10 out of 10
    lower, upper = wilson_ci(10, 10)
    assert 0.65 < lower < 0.75
    assert pytest.approx(upper, 1e-6) == 1.0


    # 50 out of 100
    lower, upper = wilson_ci(50, 100)
    assert pytest.approx(lower, 0.02) == 0.40
    assert pytest.approx(upper, 0.02) == 0.60


def test_paired_bootstrap_ci():
    # Identical systems -> diff = 0.0
    y_test = [True, False, True, True, False]
    y_base = [True, False, True, True, False]
    mean_d, ci_l, ci_u = paired_bootstrap_ci(y_test, y_base, n_bootstrap=500)
    assert mean_d == 0.0
    assert ci_l == 0.0
    assert ci_u == 0.0

    # Superior system
    y_sup = [True] * 80 + [False] * 20
    y_inf = [True] * 60 + [False] * 40
    mean_d, ci_l, ci_u = paired_bootstrap_ci(y_sup, y_inf, n_bootstrap=1000)
    assert pytest.approx(mean_d, 0.01) == 0.20
    assert ci_l > 0.05
    assert ci_u < 0.35


def test_mcnemar_exact_test():
    # 4 discordant wins, 0 losses
    y_sys = [True, True, True, True, False]
    y_base = [False, False, False, False, False]
    res = mcnemar_exact_test(y_sys, y_base)

    assert res["n10_system_wins"] == 4
    assert res["n01_baseline_wins"] == 0
    assert res["discordant_total"] == 4
    assert res["system_win_ratio"] == "4 to 0"
    assert res["p_value"] == 0.125
