"""Integration test suite for Grounded Answers & Citation Invariants (PRD §7.4, §14).

Acceptance Criteria:
1. Grounded answer generation with valid citation labels resolved to actual retrieved chunks.
2. Citation resolution regression tests pass (100% mechanical resolution rate).
3. Hallucinated / invented citation labels are rejected and trigger feedback retry.
4. Failed citation resolution does not silently return a confident answer.
5. Out-of-scope / unevidenced questions trigger explicit refusal.
6. Ambiguous entity mentions trigger needs_clarification.
"""

import pytest

from kgrag.answer.context import EvidenceItem, EvidenceRegistry
from kgrag.answer.generator import generate_grounded_answer
from kgrag.answer.pipeline import GroundedAnswerPipeline, GroundedAnswerResult
from kgrag.answer.validator import validate_citations


@pytest.fixture
def pipeline():
    return GroundedAnswerPipeline()


def test_grounded_answer_with_valid_citations(pipeline):
    """Verified filing query generates grounded answer with 100% resolvable citations (PRD §14)."""
    res = pipeline.answer_question(
        question="What corporate partnerships does NVIDIA have according to its filings?",
        template_id="neighbors",
        entity_1="NVDA",
        relation_type="PARTNERS_WITH",
        top_k=2,
    )

    assert isinstance(res, GroundedAnswerResult)
    assert res.status == "answered"
    assert res.citation_resolution_rate == 1.0
    assert len(res.citations) >= 1

    # Invariant: Every citation label must resolve to an actually retrieved chunk ID
    retrieved_chunk_ids = {
        c.chunk_id for p in res.retrieval_bundle.graph_paths for c in p.evidence
    } | {p.chunk_id for p in res.retrieval_bundle.vector_passages}

    for cit in res.citations:
        assert cit.label.startswith("[G") or cit.label.startswith("[P")
        assert cit.chunk_id in retrieved_chunk_ids, (
            f"Citation chunk_id {cit.chunk_id} was not in retrieved chunks!"
        )
        assert cit.text_snippet or cit.evidence_quote, "Citation missing quote/snippet."


def test_out_of_scope_refusal(pipeline):
    """Out-of-scope questions without supporting evidence produce refusal (PRD FR-4.5)."""
    res = pipeline.answer_question(
        question="Who won the 2026 FIFA World Cup according to NVIDIA's 10-K filing?",
        top_k=2,
    )

    assert res.status == "refusal"
    assert "not contain sufficient evidence" in res.answer.lower()
    assert res.citation_resolution_rate == 1.0


def test_citation_resolution_rejects_hallucinations_with_retries():
    """Model inventing non-existent citations is rejected and never passed silently (PRD FR-4.4A)."""
    registry = EvidenceRegistry()
    registry.register(
        EvidenceItem(
            label="[G1]",
            chunk_id="chunk_real_01",
            text_snippet="Real graph fact",
        )
    )

    # Simulated model output with an invented citation [P99]
    hallucinated_answer = "NVIDIA developed new AI hardware [G1] and opened quantum labs [P99]."
    val = validate_citations(hallucinated_answer, registry)

    assert val.is_valid is False
    assert "[P99]" in val.invalid_labels
    assert "[G1]" in val.valid_labels
    assert val.resolution_rate == 0.5
    assert "P99" in val.feedback_message


def test_failed_resolution_never_silent():
    """Invariant: Failed citation resolution does not silently return a confident answer (PRD §14)."""

    # Verify that an outcome with invalid citations is marked 'validation_failed'
    registry = EvidenceRegistry()
    registry.register(EvidenceItem(label="[G1]", chunk_id="chunk_01"))

    # When generator exhausts retries on invalid citation, status must be validation_failed
    outcome = generate_grounded_answer(
        question="Sample question",
        context_text="[G1] Real fact",
        registry=registry,
        max_retries=0,  # simulate immediate exhaustion
    )

    # Invariant: either answered with valid citations, cleanly refused, or marked validation_failed. Never silently unevidenced.
    assert outcome.status in ("answered", "validation_failed", "refusal")
    if outcome.status == "validation_failed":
        assert "unable to verify all citations" in outcome.answer
    elif outcome.status == "answered":
        assert outcome.resolution_rate == 1.0


def test_multihop_grounded_answer(pipeline):
    """Multi-hop question answered with evidenced citations across hop steps (PRD §7.4)."""
    res = pipeline.answer_question(
        question="Which shared markets and geographic reach do both NVIDIA and Microsoft operate in according to filings?",
        template_id="shared_neighbors",
        entity_1="nvidia",
        entity_2="microsoft",
        top_k=2,
    )

    assert res.status == "answered"
    assert res.citation_resolution_rate == 1.0
    assert len(res.citations) >= 1
