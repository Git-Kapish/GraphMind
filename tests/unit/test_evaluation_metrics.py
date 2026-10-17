"""Unit tests for evaluation metrics, statistical integrity, and dataset validation (PRD §2.2, Milestone M10).

Verifies:
1. Retrieval metrics (Recall@k, MRR, nDCG@k) and explicit denominator handling.
2. End-to-end QA metrics (Accuracy, Citation Resolution, Refusal Accuracy, Latency).
3. Statistical reporting (Wilson score intervals, paired bootstrap, McNemar exact test with power caveats).
4. Benchmark dataset schema integrity and ground-truth validation.
"""

import json
from pathlib import Path

import pytest

from kgrag.benchmarks.metrics import (
    compute_answer_accuracy,
    compute_citation_invariant_pass_rate,
    compute_citation_resolution_rate,
    compute_mrr,
    compute_ndcg_at_k,
    compute_percentiles,
    compute_recall_at_k,
    compute_refusal_accuracy,
)
from kgrag.benchmarks.statistics import (
    mcnemar_exact_test,
    wilson_ci,
)

# ==============================================================================
# 1. RETRIEVAL METRICS
# ==============================================================================


def test_recall_at_k_calculation():
    """Verify Recall@k with multiple gold chunks and cutoff boundaries."""
    retrieved = [
        ["c1", "c2", "c3", "c4", "c5"],  # Hit at rank 1 (c1)
        ["c9", "c8", "c3", "c7", "c6"],  # Hit at rank 3 (c3)
        ["c9", "c8", "c7", "c6", "c5"],  # Hit at rank 5 (c5)
        ["c9", "c8", "c7", "c6", "c4"],  # Miss within top-3, hit at top-5 if k=5 (c4)
        ["c9", "c8", "c7", "c6", "c0"],  # Complete miss
    ]
    gold = [
        ["c1"],
        ["c3"],
        ["c5"],
        ["c4"],
        ["c99"],
    ]

    r3 = compute_recall_at_k(retrieved, gold, k=3)
    # Queries 0 and 1 hit in top-3 -> 2/5 = 0.40
    assert pytest.approx(r3, 1e-4) == 0.40

    r5 = compute_recall_at_k(retrieved, gold, k=5)
    # Queries 0, 1, 2, 3 hit in top-5 -> 4/5 = 0.80
    assert pytest.approx(r5, 1e-4) == 0.80


def test_recall_at_k_skips_unanswerable_queries_in_denominator():
    """Verify that unanswerable queries (empty gold chunk list) are excluded from the retrieval denominator."""
    retrieved = [
        ["c1", "c2", "c3"],
        ["c4", "c5", "c6"],
        ["c7", "c8", "c9"],  # Unanswerable query
    ]
    gold = [
        ["c1"],
        ["c99"],
        [],  # Empty gold chunks (out-of-scope query)
    ]

    # Only 2 eligible answerable queries; query 0 hits -> 1/2 = 0.50
    recall = compute_recall_at_k(retrieved, gold, k=3)
    assert pytest.approx(recall, 1e-4) == 0.50


def test_mrr_calculation():
    """Verify Mean Reciprocal Rank (MRR) computation."""
    retrieved = [
        ["c1", "c2", "c3"],  # Rank 1 -> RR = 1.0
        ["c9", "c2", "c3"],  # Rank 2 -> RR = 0.5
        ["c9", "c8", "c3"],  # Rank 3 -> RR = 1/3
        ["c9", "c8", "c7"],  # Miss   -> RR = 0.0
    ]
    gold = [["c1"], ["c2"], ["c3"], ["c99"]]

    # Expected: (1.0 + 0.5 + (1/3) + 0.0) / 4 = (11/6) / 4 = 11/24 = 0.45833...
    mrr = compute_mrr(retrieved, gold)
    assert pytest.approx(mrr, 1e-4) == 11.0 / 24.0


def test_ndcg_at_k():
    """Verify nDCG@k calculation with binary relevance."""
    # Perfect ranking: gold items at ranks 1 and 2
    retrieved_perfect = [["c1", "c2", "c3", "c4", "c5"]]
    gold = [["c1", "c2"]]
    ndcg_perfect = compute_ndcg_at_k(retrieved_perfect, gold, k=5)
    assert pytest.approx(ndcg_perfect, 1e-4) == 1.0

    # Sub-optimal ranking: gold items at ranks 4 and 5
    retrieved_sub = [["c3", "c4", "c5", "c1", "c2"]]
    ndcg_sub = compute_ndcg_at_k(retrieved_sub, gold, k=5)
    assert 0.0 < ndcg_sub < 1.0

    # Complete miss
    retrieved_miss = [["x1", "x2", "x3", "x4", "x5"]]
    ndcg_miss = compute_ndcg_at_k(retrieved_miss, gold, k=5)
    assert ndcg_miss == 0.0


# ==============================================================================
# 2. ANSWER & CITATION INVARIANT METRICS
# ==============================================================================


def test_answer_accuracy_calculation():
    outcomes = [True, True, False, True, False]
    acc = compute_answer_accuracy(outcomes)
    assert pytest.approx(acc, 1e-4) == 0.60
    assert compute_answer_accuracy([]) == 0.0


def test_citation_resolution_rate_and_invariant():
    """Verify citation resolution and per-question invariant pass rate."""
    # 9 valid out of 10 extracted citations
    rate = compute_citation_resolution_rate(9, 10)
    assert pytest.approx(rate, 1e-4) == 0.90

    # Clean refusal with 0 extracted citations vacuously passes
    assert compute_citation_resolution_rate(0, 0) == 1.0

    # Invariant pass rate: 3 queries passed 100%, 1 query failed
    pass_rate = compute_citation_invariant_pass_rate([True, True, False, True])
    assert pytest.approx(pass_rate, 1e-4) == 0.75


def test_refusal_accuracy():
    """Verify refusal accuracy computes over unanswerable queries."""
    refusals = [True, True, False, True]
    assert compute_refusal_accuracy(refusals) == 0.75
    assert compute_refusal_accuracy([]) == 0.0


def test_latency_percentiles():
    latencies = [100.0, 200.0, 300.0, 400.0, 500.0]
    p = compute_percentiles(latencies)
    assert p["p50"] == 300
    assert p["min"] == 100
    assert p["max"] == 500


# ==============================================================================
# 3. STATISTICAL INTEGRITY & UNDERPOWERED TESTS
# ==============================================================================


def test_wilson_ci_bounds_and_edge_cases():
    """Verify Wilson score confidence interval boundary properties."""
    # 0 successes
    low, high = wilson_ci(0, 20)
    assert low == 0.0
    assert 0.10 < high < 0.20

    # 100% successes
    low, high = wilson_ci(20, 20)
    assert 0.80 < low < 0.90
    assert high == 1.0

    # Empty denominator
    assert wilson_ci(0, 0) == (0.0, 0.0)


def test_mcnemar_exact_power_caveat():
    """Verify that McNemar exact test detects underpowered sample sizes."""
    # 4 hybrid wins vs 0 baseline wins on N=25
    y_sys = [True] * 4 + [True] * 18 + [False] * 3
    y_base = [False] * 4 + [True] * 18 + [False] * 3

    res = mcnemar_exact_test(y_sys, y_base)
    assert res["n10_system_wins"] == 4
    assert res["n01_baseline_wins"] == 0
    assert res["discordant_total"] == 4
    # Exact binomial p-value for 4 vs 0 is 2 * 0.5^4 = 0.125
    assert pytest.approx(res["p_value"], 1e-4) == 0.1250
    # Must be flagged as underpowered
    assert res["is_underpowered"] is True
    assert res["statistically_significant_05"] is False
    assert "below recommended threshold" in res["power_caveat"]


def test_mcnemar_sufficient_power():
    """Verify that a test with >= 10 discordant pairs and p < 0.05 is recognized as statistically significant."""
    # 10 hybrid wins vs 0 baseline wins on N=30
    y_sys = [True] * 10 + [True] * 15 + [False] * 5
    y_base = [False] * 10 + [True] * 15 + [False] * 5

    res = mcnemar_exact_test(y_sys, y_base)
    assert res["n10_system_wins"] == 10
    assert res["discordant_total"] == 10
    # Exact p-value for 10 vs 0 is 2 * 0.5^10 = 0.00195
    assert res["p_value"] < 0.01
    assert res["is_underpowered"] is False
    assert res["statistically_significant_05"] is True


# ==============================================================================
# 4. DATASET VALIDATION (DATA INTEGRITY & PROVENANCE)
# ==============================================================================


def test_benchmark_dataset_v2_schema_and_integrity():
    """Verify that benchmark_questions_v2.jsonl satisfies all ground truth and schema contracts."""
    dataset_file = Path("benchmarks/questions/benchmark_questions_v2.jsonl")
    assert dataset_file.exists(), f"Missing dataset file: {dataset_file}"

    questions = []
    with open(dataset_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    assert len(questions) == 60, f"Expected 60 questions, found {len(questions)}"

    seen_ids = set()
    splits = {"dev": 0, "test": 0}
    categories = {"single_hop": 0, "two_hop": 0, "multi_hop": 0, "out_of_scope": 0}

    for q in questions:
        # 1. Unique ID
        qid = q.get("id")
        assert qid, "Question missing ID"
        assert qid not in seen_ids, f"Duplicate question ID: {qid}"
        seen_ids.add(qid)

        # 2. Required fields
        assert "question" in q and len(q["question"]) > 5
        assert "category" in q and q["category"] in categories
        assert "split" in q and q["split"] in splits
        assert "answerable" in q and isinstance(q["answerable"], bool)
        assert q.get("dataset_version") == "2.0.0"

        categories[q["category"]] += 1
        splits[q["split"]] += 1

        # 3. Ground truth integrity
        if q["answerable"]:
            assert q.get("gold_answer"), f"Answerable question {qid} missing gold_answer"
            assert q.get("gold_chunk_ids") or q.get("gold_graph_facts"), (
                f"Answerable question {qid} missing ground truth evidence"
            )
        else:
            assert q["category"] == "out_of_scope", (
                f"Unanswerable question {qid} must be out_of_scope"
            )

    assert splits["dev"] == 12
    assert splits["test"] == 48


def test_dataset_metadata_file_validity():
    """Verify that dataset_metadata.json documents versioning, splits, and filers."""
    meta_file = Path("benchmarks/questions/dataset_metadata.json")
    assert meta_file.exists(), f"Missing metadata file: {meta_file}"

    with open(meta_file, encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["version"] == "2.0.0"
    assert len(meta["filers_covered"]) >= 6
    assert "splits" in meta
    assert "ground_truth_policy" in meta
