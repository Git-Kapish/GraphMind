"""Unit tests for Mechanical Citation Resolution Validator (PRD §7.4, FR-4.4A, Milestone M6)."""

import pytest

from kgrag.answer.context import EvidenceItem, EvidenceRegistry
from kgrag.answer.validator import (
    parse_citation_labels,
    validate_citations,
)


@pytest.fixture
def mock_registry():
    registry = EvidenceRegistry()
    registry.register(
        EvidenceItem(label="[G1]", chunk_id="chunk_graph_01", text_snippet="Graph fact 1")
    )
    registry.register(
        EvidenceItem(label="[G2]", chunk_id="chunk_graph_02", text_snippet="Graph fact 2")
    )
    registry.register(EvidenceItem(label="[P1]", chunk_id="chunk_vec_01", text_snippet="Passage 1"))
    registry.register(EvidenceItem(label="[P2]", chunk_id="chunk_vec_02", text_snippet="Passage 2"))
    return registry


def test_parse_citation_labels():
    """Verify regex extraction of bracketed citation labels."""
    text = (
        "NVIDIA partnered with Microsoft [G1] to expand Azure data centers [P1] and AI clouds [G2]."
    )
    labels = parse_citation_labels(text)
    assert labels == ["[G1]", "[P1]", "[G2]"]

    # No citations
    assert parse_citation_labels("Plain text without citations.") == []


def test_validate_citations_all_valid(mock_registry):
    """Verify 100% valid citations pass mechanical validation invariant."""
    answer = "NVIDIA partnered with Microsoft [G1]. Their data center revenues increased significantly [P2]."
    result = validate_citations(answer, mock_registry)

    assert result.is_valid is True
    assert result.is_refusal is False
    assert result.resolution_rate == 1.0
    assert result.invalid_labels == []
    assert len(result.resolved_citations) == 2
    assert result.resolved_citations[0].chunk_id == "chunk_graph_01"
    assert result.resolved_citations[1].chunk_id == "chunk_vec_02"


def test_validate_citations_hallucinated_label_rejected(mock_registry):
    """Verify hallucinated/invented citation labels are strictly rejected (PRD FR-4.4A)."""
    # [P99] is invented by model and not in mock_registry
    answer = "NVIDIA partnered with Microsoft [G1] and also launched quantum GPUs [P99]."
    result = validate_citations(answer, mock_registry)

    assert result.is_valid is False
    assert "[P99]" in result.invalid_labels
    assert "[G1]" in result.valid_labels
    assert result.resolution_rate == 0.5  # 1 of 2 valid
    assert "P99" in result.feedback_message
    assert "You may ONLY cite valid labels" in result.feedback_message


def test_validate_citations_zero_citations_rejected_on_factual_answer(mock_registry):
    """Verify factual answer without citations is rejected."""
    answer = "NVIDIA is a technology company headquartered in Santa Clara."
    result = validate_citations(answer, mock_registry)

    assert result.is_valid is False
    assert result.resolution_rate == 0.0
    assert "Your answer did not cite any evidence labels" in result.feedback_message


def test_validate_citations_refusal_accepted_with_zero_citations(mock_registry):
    """Verify explicit refusal statement is accepted with 0 citations (PRD FR-4.5)."""
    refusal = "The provided filings do not contain sufficient evidence to answer this question."
    result = validate_citations(refusal, mock_registry)

    assert result.is_valid is True
    assert result.is_refusal is True
    assert result.resolution_rate == 1.0
    assert len(result.resolved_citations) == 0


def test_citation_invariant_no_silent_failure(mock_registry):
    """Verify invariant: failed resolution never returns a confident passing result."""
    bad_answer = "Everything is great [G99] and profits grew [P88]."
    result = validate_citations(bad_answer, mock_registry)

    assert result.is_valid is False
    assert len(result.invalid_labels) == 2
    assert len(result.valid_labels) == 0
    assert result.resolution_rate == 0.0
