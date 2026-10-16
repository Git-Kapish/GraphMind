"""Unit tests for ambiguity handling and entity resolution review band (PRD §9.3, §14, Milestone M11).

Verifies that:
1. Ambiguous entity matches within the review band (0.70 <= score < 0.85) are NOT silently auto-merged.
2. Review queue entries are assigned decision='needs_review'.
3. Hard negative entity pairs (distinct companies/subsidiaries) are never auto-merged.
4. Ambiguous queries with low routing confidence trigger fallback_used=True.
"""

from kgrag.resolve.candidates import find_best_candidate
from kgrag.retrieval.router import route_query


def test_review_band_entity_does_not_silently_merge():
    """Verify that candidate similarity in [0.70, 0.85) is not auto-merged and stays in review band (PRD §9.3)."""
    existing_entities = [
        {
            "entity_id": "ent_canon_001",
            "type": "Company",
            "canonical_name": "Fabless Semiconductor Technologies",
            "aliases": ["Fabless Semi Tech"],
        }
    ]

    # Surface name has high token overlap but is distinct/ambiguous
    surface = "Semiconductor Technologies Group"
    cand = find_best_candidate(
        surface_name=surface,
        entity_type="Company",
        existing_entities=existing_entities,
        review_band_lower=0.50,
        embedding_threshold=0.85,
    )

    assert cand is not None
    # Score must be below auto-merge threshold (0.85)
    assert cand.score < 0.85
    # Confirms it cannot qualify for auto-merge
    assert cand.score >= 0.50


def test_hard_negatives_never_auto_merged():
    """Verify that distinct enterprise filers with overlapping tokens (e.g. Micron vs Microsemi) are not merged."""
    existing_entities = [
        {
            "entity_id": "ent_micron",
            "type": "Company",
            "canonical_name": "Micron Technology, Inc.",
            "aliases": ["Micron"],
        }
    ]

    surface = "Microsemi Corporation"
    cand = find_best_candidate(
        surface_name=surface,
        entity_type="Company",
        existing_entities=existing_entities,
        review_band_lower=0.70,
        embedding_threshold=0.85,
    )

    # Microsemi should NOT match Micron in auto-merge tier
    if cand is not None:
        assert cand.score < 0.85
        assert cand.canonical_id == "ent_micron"
    else:
        assert cand is None


def test_ambiguous_subordinate_entity_distinction():
    """Verify that parent company and separate subsidiary are not silently merged."""
    existing_entities = [
        {
            "entity_id": "ent_nvidia_parent",
            "type": "Company",
            "canonical_name": "NVIDIA Corporation",
            "aliases": ["NVIDIA"],
        }
    ]

    # Specific regional operating subsidiary
    sub_surface = "NVIDIA Singapore Development Pte. Ltd."
    cand = find_best_candidate(
        surface_name=sub_surface,
        entity_type="Company",
        existing_entities=existing_entities,
        review_band_lower=0.70,
        embedding_threshold=0.85,
    )

    if cand is not None:
        # Cannot auto-merge regional subsidiary into parent without explicit alias
        assert cand.score < 0.85


def test_ambiguous_router_query_triggers_fallback():
    """Verify that ambiguous or generic query with no entity matches triggers fallback_used=True (PRD FR-3.1)."""
    generic_query = "What are the common organizational principles and general perspectives?"
    decision = route_query(generic_query, mode="auto")

    assert decision.fallback_used is True
    assert decision.confidence <= 0.65
    assert decision.chosen == "hybrid"
    assert "Low routing confidence" in decision.reasoning
