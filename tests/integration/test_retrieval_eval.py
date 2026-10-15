"""Integration tests for pre-routing retrieval evaluation harness (PRD FR-2.3, Milestone M4)."""

import pytest
from pathlib import Path

from kgrag.evaluation.retrieval_eval import evaluate_retrieval


def test_retrieval_evaluation_benchmark_runs_and_passes_gate():
    """Verify that retrieval evaluation runs across 40 questions and satisfies gate criteria."""
    result = evaluate_retrieval(
        dataset_path="benchmarks/questions/retrieval_eval_pairs.jsonl",
        output_json_path="benchmarks/results/retrieval_eval_m4.json",
        output_doc_path="docs/retrieval_eval.md",
    )

    assert result["total_questions"] == 40
    # Gate checks
    assert result["recall_at_5"] >= 0.60, f"Expected Recall@5 >= 60%, got {result['recall_at_5']*100:.1f}%"
    assert result["recall_at_10"] >= 0.70, f"Expected Recall@10 >= 70%, got {result['recall_at_10']*100:.1f}%"
    assert result["mrr"] > 0.40, f"Expected MRR > 0.40, got {result['mrr']:.4f}"
    assert result["avg_latency_ms"] < 500.0, f"Expected latency < 500ms, got {result['avg_latency_ms']:.1f}ms"

    # Verify generated artifact files exist
    assert Path("benchmarks/results/retrieval_eval_m4.json").exists()
    assert Path("docs/retrieval_eval.md").exists()
