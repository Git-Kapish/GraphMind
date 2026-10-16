"""Unit tests for entity candidate matching and similarity scoring (PRD FR-1.4, Milestone M3)."""

import pytest

from kgrag.resolve.candidates import (
    cosine_similarity,
    find_best_candidate,
    jaccard_similarity,
    token_similarity,
)


def test_jaccard_similarity():
    set_a = {"intel", "corporation"}
    set_b = {"intel", "inc"}
    # Intersection: {"intel"} (1), Union: {"intel", "corporation", "inc"} (3) -> 1/3
    assert pytest.approx(jaccard_similarity(set_a, set_b), 0.01) == 0.333

    assert jaccard_similarity(set(), {"test"}) == 0.0
    assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert pytest.approx(cosine_similarity(v1, v2), 0.001) == 1.0
    assert pytest.approx(cosine_similarity(v1, v3), 0.001) == 0.0


def test_token_similarity_hard_negatives():
    # Hard negative: Competitors / different companies with word overlap
    score_applied = token_similarity("Applied Materials", "Applied Optoelectronics")
    assert score_applied < 0.70  # Must be strictly below the review band!

    score_western = token_similarity("Western Digital", "Western Union")
    assert score_western < 0.70

    score_micro = token_similarity("Microchip Technology", "Micron Technology")
    assert score_micro < 0.70

    score_apple = token_similarity("Apple Inc.", "Apple Hospitality REIT")
    assert score_apple < 0.70


def test_find_best_candidate_exact_and_alias():
    existing = [
        {
            "entity_id": "ent_nvda",
            "canonical_name": "NVIDIA Corporation",
            "type": "Company",
            "aliases": ["NVIDIA", "Nvidia Corp", "NVDA"],
        },
        {
            "entity_id": "ent_tsmc",
            "canonical_name": "Taiwan Semiconductor Manufacturing Company",
            "type": "Company",
            "aliases": ["TSMC", "Taiwan Semiconductor"],
        },
    ]

    # Exact canonical match
    cand = find_best_candidate("NVIDIA Corporation", "Company", existing)
    assert cand is not None
    assert cand.canonical_id == "ent_nvda"
    assert cand.score == 1.0
    assert cand.method == "exact_match"

    # Alias match
    cand_alias = find_best_candidate("TSMC", "Company", existing)
    assert cand_alias is not None
    assert cand_alias.canonical_id == "ent_tsmc"
    assert cand_alias.score == 1.0

    # Type mismatch rejected
    cand_mismatch = find_best_candidate("NVIDIA Corporation", "Person", existing)
    assert cand_mismatch is None


def test_find_best_candidate_hard_negatives_rejected():
    existing = [
        {
            "entity_id": "ent_applied",
            "canonical_name": "Applied Materials",
            "type": "Company",
            "aliases": [],
        }
    ]

    cand = find_best_candidate(
        "Applied Optoelectronics", "Company", existing, review_band_lower=0.70
    )
    assert cand is None  # Below review threshold, correctly treated as distinct new
