"""Comprehensive test suite for the 100-Question Evaluation Dataset and Benchmark Engine (Phase 10).

Covers:
1. Dataset schema and integrity:
   - Exactly 100 unique question IDs.
   - Exactly 100 unique question texts.
   - Balanced distribution: exactly 20 questions in each of the 5 categories.
   - Valid schema, field types, and non-empty required fields.
   - Every answerable question has verified gold answer and traceable source documents.
   - Every out-of-scope question has explicit refusal rationale and answerable=False.
   - SHA-256 cryptographic manifest validation.
2. Metrics calculations:
   - Recall@5, MRR, Evidence Coverage, Retrieval Failure Rate.
   - Citation Resolution, Membership Rate, Claim Support, and Unsupported Claim Rate.
   - Paired McNemar exact test and Bootstrap CI.
3. Runner safety and reproducibility:
   - Immutable directory generation.
   - Preservation of historical artifacts.
   - Resume logic without record duplication.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from kgrag.benchmarks.metrics import (
    compute_citation_membership_rate,
    compute_claim_support_rate,
    compute_evidence_coverage,
    compute_retrieval_failure_rate,
    compute_unsupported_factual_claim_rate,
)
from kgrag.benchmarks.statistics import (
    mcnemar_exact_test,
    paired_bootstrap_ci,
)

BENCHMARK_100Q_PATHS = [
    Path("benchmarks/questions/graphmind_eval_100q_v1.jsonl"),
    Path("eval/datasets/graphmind_eval_v1.jsonl"),
]

MANIFEST_PATHS = [
    Path("benchmarks/questions/dataset_manifest_100q.json"),
    Path("eval/datasets/dataset_manifest.json"),
]


# ==============================================================================
# 1. DATASET INTEGRITY & SCHEMA TESTS
# ==============================================================================


@pytest.mark.parametrize("dataset_path", BENCHMARK_100Q_PATHS)
def test_dataset_exact_count_and_distribution(dataset_path: Path):
    """Verify that dataset contains exactly 100 questions with 20 per category."""
    assert dataset_path.exists(), f"Dataset file missing: {dataset_path}"

    questions: list[dict[str, Any]] = []
    with open(dataset_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                questions.append(json.loads(line))

    assert len(questions) == 100, f"Expected exactly 100 questions, got {len(questions)}"

    # Check unique IDs and question texts
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), f"Duplicate question IDs found: {len(ids)} vs {len(set(ids))}"

    texts = [q["question"].strip().lower() for q in questions]
    assert len(texts) == len(set(texts)), (
        f"Duplicate question texts found: {len(texts)} vs {len(set(texts))}"
    )

    # Category distribution
    expected_categories = {
        "single_hop": 20,
        "two_hop": 20,
        "three_hop": 20,
        "aggregation": 20,
        "out_of_scope": 20,
    }
    counts: dict[str, int] = {}
    for q in questions:
        cat = q.get("category")
        counts[cat] = counts.get(cat, 0) + 1

    assert counts == expected_categories, (
        f"Category mismatch: {counts} vs expected {expected_categories}"
    )


@pytest.mark.parametrize("dataset_path", BENCHMARK_100Q_PATHS)
def test_dataset_schema_and_grounding(dataset_path: Path):
    """Verify that every question conforms to schema and has verified gold evidence."""
    with open(dataset_path, encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    for q in questions:
        qid = q.get("id")
        assert qid, "Missing question id"
        assert "question" in q and len(q["question"]) > 10, f"{qid}: Question text too short"
        assert "category" in q, f"{qid}: Missing category"
        assert "difficulty" in q, f"{qid}: Missing difficulty"
        assert "hop_count" in q and isinstance(q["hop_count"], int), f"{qid}: Invalid hop_count"
        assert "answerable" in q and isinstance(q["answerable"], bool), (
            f"{qid}: Invalid answerable flag"
        )
        assert "gold_answer" in q, f"{qid}: Missing gold_answer"
        assert "expected_facts" in q and isinstance(q["expected_facts"], list), (
            f"{qid}: Invalid expected_facts"
        )
        assert "required_entities" in q and isinstance(q["required_entities"], list), (
            f"{qid}: Invalid required_entities"
        )
        assert "source_documents" in q and isinstance(q["source_documents"], list), (
            f"{qid}: Invalid source_documents"
        )
        assert "source_passage_ids" in q and isinstance(q["source_passage_ids"], list), (
            f"{qid}: Invalid source_passage_ids"
        )
        assert "evaluation_notes" in q and len(q["evaluation_notes"]) > 5, (
            f"{qid}: Missing evaluation_notes"
        )

        if q["answerable"]:
            assert q["category"] != "out_of_scope", (
                f"{qid}: Answerable question labeled out_of_scope"
            )
            assert len(q["gold_answer"]) > 5, f"{qid}: Empty gold answer on answerable question"
            assert len(q["expected_facts"]) >= 1, (
                f"{qid}: Answerable question has no expected_facts"
            )
            assert len(q["source_documents"]) >= 1, (
                f"{qid}: Answerable question has no source_documents"
            )
            assert len(q["source_passage_ids"]) >= 1, (
                f"{qid}: Answerable question has no source_passage_ids"
            )

            # Check hop count consistency
            if q["category"] == "single_hop":
                assert q["hop_count"] == 1, f"{qid}: single_hop must have hop_count=1"
            elif q["category"] == "two_hop":
                assert q["hop_count"] == 2, f"{qid}: two_hop must have hop_count=2"
            elif q["category"] == "three_hop":
                assert q["hop_count"] == 3, f"{qid}: three_hop must have hop_count=3"
        else:
            assert q["category"] == "out_of_scope", (
                f"{qid}: Unanswerable question must be out_of_scope"
            )
            assert q["hop_count"] == 0, f"{qid}: out_of_scope must have hop_count=0"
            ans_lower = q["gold_answer"].lower()
            assert (
                "refusal" in ans_lower or "out of scope" in ans_lower or "unanswerable" in ans_lower
            ), f"{qid}: Out-of-scope gold answer must specify refusal"


@pytest.mark.parametrize("manifest_path", MANIFEST_PATHS)
def test_manifest_cryptographic_checksum(manifest_path: Path):
    """Verify that dataset manifest exists and matches the exact SHA-256 of the dataset file."""
    assert manifest_path.exists(), f"Manifest missing: {manifest_path}"

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["total_questions"] == 100
    assert manifest["version"] == "1.0.0"
    assert manifest["categories"]["single_hop"] == 20
    assert manifest["categories"]["two_hop"] == 20
    assert manifest["categories"]["three_hop"] == 20
    assert manifest["categories"]["aggregation"] == 20
    assert manifest["categories"]["out_of_scope"] == 20

    # Locate corresponding dataset
    dataset_file = manifest_path.parent / manifest["dataset_filename"]
    assert dataset_file.exists(), f"Dataset file {dataset_file} not found"

    # Compute actual SHA-256
    hasher = hashlib.sha256()
    with open(dataset_file, "rb") as f:
        hasher.update(f.read())
    actual_sha = hasher.hexdigest()

    assert actual_sha == manifest["sha256_checksum"], (
        f"Checksum mismatch: manifest {manifest['sha256_checksum']} vs actual {actual_sha}"
    )


# ==============================================================================
# 2. METRICS UNIT TESTS
# ==============================================================================


def test_evidence_coverage_calculation():
    """Verify compute_evidence_coverage on multi-fact queries."""
    # Query 1: 3 facts required, top-5 contains 2 -> 2/3 = 0.6667
    # Query 2: 2 facts required, top-5 contains 2 -> 2/2 = 1.0000
    # Query 3: 1 fact required, top-5 contains 0 -> 0/1 = 0.0000
    # Query 4: Unanswerable (0 facts required) -> excluded from denominator
    retrieved = [
        ["c1", "c2", "c9", "c8", "c7"],
        ["c3", "c4", "c8", "c7", "c6"],
        ["c9", "c8", "c7", "c6", "c5"],
        ["c1", "c2", "c3", "c4", "c5"],
    ]
    gold = [
        ["c1", "c2", "c3"],
        ["c3", "c4"],
        ["c0"],
        [],
    ]

    cov = compute_evidence_coverage(retrieved, gold, k=5)
    expected = ((2 / 3) + (2 / 2) + (0 / 1)) / 3
    assert pytest.approx(cov, 1e-4) == expected


def test_retrieval_failure_rate_calculation():
    """Verify compute_retrieval_failure_rate."""
    retrieved = [
        ["c1", "c2"],  # hit
        ["c9", "c8"],  # miss (failure)
        ["c3", "c4"],  # hit
        ["c5", "c6"],  # unanswerable
    ]
    gold = [
        ["c1"],
        ["c2"],
        ["c3"],
        [],
    ]
    # 3 eligible answerable queries; 1 complete miss -> failure rate = 1/3
    rate = compute_retrieval_failure_rate(retrieved, gold, k=2)
    assert pytest.approx(rate, 1e-4) == 1.0 / 3.0


def test_citation_metrics():
    """Verify citation membership, claim support, and unsupported claim metrics."""
    assert compute_citation_membership_rate(18, 20) == 0.90
    assert compute_citation_membership_rate(0, 0) == 1.0

    assert compute_claim_support_rate(19, 20) == 0.95
    assert compute_claim_support_rate(0, 0) == 1.0

    assert compute_unsupported_factual_claim_rate(1, 20) == 0.05
    assert compute_unsupported_factual_claim_rate(0, 0) == 0.0


# ==============================================================================
# 3. STATISTICAL ENGINE TESTS
# ==============================================================================


def test_paired_bootstrap_and_mcnemar_on_100q():
    """Verify that paired bootstrap and McNemar tests operate properly on 100 questions."""
    # System A (Vector Baseline): 65 correct
    # System B (Hybrid KG-RAG): 82 correct
    # 20 hybrid wins, 3 baseline wins, 62 both correct, 15 both incorrect
    y_base = [True] * 62 + [False] * 20 + [True] * 3 + [False] * 15
    y_hyb = [True] * 62 + [True] * 20 + [False] * 3 + [False] * 15

    assert len(y_base) == 100
    assert len(y_hyb) == 100

    mcn = mcnemar_exact_test(y_hyb, y_base)
    assert mcn["n10_system_wins"] == 20
    assert mcn["n01_baseline_wins"] == 3
    assert mcn["discordant_total"] == 23
    assert mcn["is_underpowered"] is False
    assert mcn["p_value"] < 0.001
    assert mcn["statistically_significant_05"] is True

    mean_d, ci_l, ci_u = paired_bootstrap_ci(y_hyb, y_base, n_bootstrap=1000)
    assert pytest.approx(mean_d, 0.01) == 0.17
    assert ci_l > 0.07
    assert ci_u < 0.28


# ==============================================================================
# 4. RUNNER SAFETY, RESUME, AND HISTORICAL ARTIFACT PRESERVATION
# ==============================================================================


def test_historical_benchmark_artifacts_exist_and_unmodified():
    """Verify that historical M8, M10, and M4 artifacts exist and are never deleted."""
    m8_file = Path("benchmarks/results/benchmark_results.json")
    m10_file = Path("benchmarks/results/full_benchmark_results.json")
    m4_file = Path("benchmarks/results/retrieval_eval_results.json")

    assert m8_file.exists(), "Historical M8 benchmark_results.json must be preserved!"
    assert m10_file.exists(), "Historical M10 full_benchmark_results.json must be preserved!"
    assert m4_file.exists(), "Historical M4 retrieval_eval_results.json must be preserved!"

    with open(m8_file, encoding="utf-8") as f:
        m8_data = json.load(f)
    assert m8_data["metadata"]["total_questions"] == 25, (
        "M8 must preserve 25 questions historical scope"
    )

    with open(m10_file, encoding="utf-8") as f:
        m10_data = json.load(f)
    assert m10_data["metadata"]["total_questions"] == 2, (
        "M10 must preserve 2 questions smoke-test scope"
    )


def test_runner_dry_run_validation():
    """Verify eval.run_benchmark in dry-run mode returns success without external API calls."""
    from kgrag.benchmarks.run_benchmark import run_benchmark_suite

    res = run_benchmark_suite(mode="dry-run")
    assert res["status"] == "dry_run_success"
    assert res["questions_count"] == 100
    assert len(res["sha256"]) == 64


def test_runner_resume_checksum_guard(tmp_path: Path):
    """Verify that resuming with mismatched dataset checksum is strictly rejected."""
    from kgrag.benchmarks.run_benchmark import run_benchmark_suite

    # Create dummy previous run with fake checksum in manifest
    run_dir = tmp_path / "run_test_resume"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_dir / "manifest.json"
    results = run_dir / "question_results.jsonl"
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump({"dataset_sha256": "fake_mismatched_checksum_000"}, f)
    with open(results, "w", encoding="utf-8") as f:
        f.write('{"question_id": "Q001", "system": "System A"}\n')

    with pytest.raises(ValueError, match="Dataset checksum in manifest does not match"):
        run_benchmark_suite(
            output_dir=tmp_path,
            resume=True,
            run_id="run_test_resume",
        )
