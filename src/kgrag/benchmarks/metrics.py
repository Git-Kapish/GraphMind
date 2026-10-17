"""Formally defined evaluation metrics and statistical calculators (PRD §2.2, Milestone M10).

Provides pure, testable metric calculations with explicit denominators:
1. Retrieval Metrics:
   - Recall@k: Proportion of answerable queries where at least one gold chunk is in top-k.
   - Mean Reciprocal Rank (MRR): Mean of 1 / rank of first gold chunk.
   - nDCG@k: Normalized Discounted Cumulative Gain at cutoff k with binary or graded relevance.
2. Answer & Grounding Metrics:
   - Answer Accuracy: Proportion of questions with correct factual answer / refusal.
   - Citation Resolution Rate: Proportion of returned citations resolving to retrieved evidence.
   - Citation Invariant Pass Rate: Proportion of queries with 100% citation resolution.
   - Refusal Accuracy: Proportion of unanswerable questions correctly refused.
   - Claim Support Rate: Proportion of citations verified as supported by evidence.
3. Latency & Performance:
   - p50 (median) and p95 latency in milliseconds.
"""

import math
from collections.abc import Sequence

import numpy as np


def compute_recall_at_k(
    retrieved_chunk_ids_per_query: Sequence[Sequence[str]],
    gold_chunk_ids_per_query: Sequence[Sequence[str]],
    k: int = 5,
) -> float:
    """Calculate Recall@k across queries.

    Denominator: Number of queries that have non-empty gold chunk IDs (answerable queries).
    Numerator: Count of queries where at least one gold chunk appears in top-k retrieved chunks.
    """
    if len(retrieved_chunk_ids_per_query) != len(gold_chunk_ids_per_query):
        raise ValueError("Lengths of retrieved and gold lists must match.")

    eligible = 0
    hits = 0

    for retrieved, gold in zip(retrieved_chunk_ids_per_query, gold_chunk_ids_per_query):
        gold_set = set(gold)
        if not gold_set:
            continue  # Skip unanswerable queries from retrieval denominator

        eligible += 1
        top_k = set(retrieved[:k])
        if gold_set.intersection(top_k):
            hits += 1

    return (hits / eligible) if eligible > 0 else 0.0


def compute_mrr(
    retrieved_chunk_ids_per_query: Sequence[Sequence[str]],
    gold_chunk_ids_per_query: Sequence[Sequence[str]],
) -> float:
    """Calculate Mean Reciprocal Rank (MRR).

    Denominator: Number of queries with non-empty gold chunk IDs.
    Reciprocal rank for a query is 1 / first_gold_rank (1-indexed), or 0.0 if not found.
    """
    if len(retrieved_chunk_ids_per_query) != len(gold_chunk_ids_per_query):
        raise ValueError("Lengths of retrieved and gold lists must match.")

    eligible = 0
    rr_sum = 0.0

    for retrieved, gold in zip(retrieved_chunk_ids_per_query, gold_chunk_ids_per_query):
        gold_set = set(gold)
        if not gold_set:
            continue

        eligible += 1
        rr = 0.0
        for rank, cid in enumerate(retrieved, start=1):
            if cid in gold_set:
                rr = 1.0 / rank
                break
        rr_sum += rr

    return (rr_sum / eligible) if eligible > 0 else 0.0


def compute_ndcg_at_k(
    retrieved_chunk_ids_per_query: Sequence[Sequence[str]],
    gold_chunk_ids_per_query: Sequence[Sequence[str]],
    k: int = 5,
) -> float:
    """Calculate Normalized Discounted Cumulative Gain (nDCG@k) with binary relevance."""
    if len(retrieved_chunk_ids_per_query) != len(gold_chunk_ids_per_query):
        raise ValueError("Lengths of retrieved and gold lists must match.")

    eligible = 0
    ndcg_sum = 0.0

    for retrieved, gold in zip(retrieved_chunk_ids_per_query, gold_chunk_ids_per_query):
        gold_set = set(gold)
        if not gold_set:
            continue

        eligible += 1
        # DCG@k
        dcg = 0.0
        for i, cid in enumerate(retrieved[:k], start=1):
            rel = 1.0 if cid in gold_set else 0.0
            dcg += rel / math.log2(i + 1)

        # Ideal DCG@k (IDCG)
        ideal_hits = min(len(gold_set), k)
        idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))

        if idcg > 0.0:
            ndcg_sum += dcg / idcg

    return (ndcg_sum / eligible) if eligible > 0 else 0.0


def compute_answer_accuracy(
    outcomes: Sequence[bool],
) -> float:
    """Calculate overall answer accuracy.

    Denominator: Total number of evaluated questions.
    """
    total = len(outcomes)
    if total == 0:
        return 0.0
    return sum(1 for c in outcomes if c) / total


def compute_citation_resolution_rate(
    total_valid_citations: int,
    total_extracted_citations: int,
) -> float:
    """Calculate aggregate citation resolution rate across all returned citations.

    Denominator: Total count of citation labels extracted from model answers.
    Numerator: Count of citation labels that strictly resolved to retrieved evidence chunks.
    """
    if total_extracted_citations <= 0:
        return (
            1.0  # Zero citations produced (e.g. on clean refusals) vacuously satisfies resolution
        )
    return total_valid_citations / total_extracted_citations


def compute_citation_invariant_pass_rate(
    question_validation_results: Sequence[bool],
) -> float:
    """Calculate proportion of questions where 100% of citations resolved (Invariant Pass Rate).

    Denominator: Total number of questions answered.
    """
    total = len(question_validation_results)
    if total == 0:
        return 0.0
    return sum(1 for passed in question_validation_results if passed) / total


def compute_refusal_accuracy(
    refusal_outcomes: Sequence[bool],
) -> float:
    """Calculate refusal accuracy on unanswerable/out-of-scope questions.

    Denominator: Total number of unanswerable/out-of-scope questions.
    """
    total = len(refusal_outcomes)
    if total == 0:
        return 0.0
    return sum(1 for c in refusal_outcomes if c) / total


def compute_percentiles(latencies_ms: Sequence[float]) -> dict[str, int]:
    """Compute p50 and p95 latency in milliseconds."""
    if not latencies_ms:
        return {"p50": 0, "p95": 0, "min": 0, "max": 0, "mean": 0}
    arr = np.array(latencies_ms, dtype=float)
    return {
        "p50": int(np.percentile(arr, 50)),
        "p95": int(np.percentile(arr, 95)),
        "min": int(np.min(arr)),
        "max": int(np.max(arr)),
        "mean": int(np.mean(arr)),
    }
