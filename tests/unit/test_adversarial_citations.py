"""Automated Adversarial Citation Tests (Phase 6 / PRD §7.4, FR-4.4A).

Verifies the mechanical citation resolution validator and claim grounding against 9 adversarial scenarios:
1. Valid citation to retrieved evidence.
2. Citation to a nonexistent passage ID.
3. Citation to a real passage that was not retrieved for the current request.
4. Citation that resolves but contradicts the associated claim.
5. Answer containing a material factual claim without a citation.
6. Malformed citation syntax.
7. Duplicate citations and multiple claims sharing evidence.
8. A graph-derived fact with a missing or invalid source-chunk association.
9. A model response containing citation-like identifiers never registered in the request evidence registry.
"""

from unittest.mock import MagicMock

import pytest

from kgrag.answer.context import EvidenceItem, EvidenceRegistry
from kgrag.answer.validator import (
    parse_citation_labels,
    validate_citations,
    verify_claim_support,
)


@pytest.fixture
def sample_registry() -> EvidenceRegistry:
    """Fixture providing a standard request-scoped evidence registry with 2 graph facts and 2 passages."""
    reg = EvidenceRegistry()
    reg.register(
        EvidenceItem(
            label="[G1]",
            chunk_id="chunk_nvda_graph_001",
            doc_id="NVDA_2024_10K",
            company="NVIDIA Corporation",
            ticker="NVDA",
            section_path="Item 1",
            text_snippet="Jensen Huang is founder, President, and CEO.",
            evidence_quote="Jensen Huang founded NVIDIA in 1993 and serves as President and CEO.",
            relation_type="OFFICER_OF",
        )
    )
    reg.register(
        EvidenceItem(
            label="[G2]",
            chunk_id="chunk_nvda_graph_002",
            doc_id="NVDA_2024_10K",
            company="NVIDIA Corporation",
            ticker="NVDA",
            section_path="Item 1",
            text_snippet="NVIDIA completed acquisition of Mellanox Technologies in April 2020.",
            evidence_quote="In April 2020, we completed our acquisition of Mellanox for $6.9 billion.",
            relation_type="ACQUIRED",
        )
    )
    reg.register(
        EvidenceItem(
            label="[P1]",
            chunk_id="chunk_amd_vec_001",
            doc_id="AMD_2024_10K",
            company="Advanced Micro Devices, Inc.",
            ticker="AMD",
            section_path="Item 1",
            text_snippet="AMD completed the acquisition of Xilinx in February 2022.",
        )
    )
    reg.register(
        EvidenceItem(
            label="[P2]",
            chunk_id="chunk_aapl_vec_001",
            doc_id="AAPL_2024_10K",
            company="Apple Inc.",
            ticker="AAPL",
            section_path="Item 7",
            text_snippet="Apple total net sales were $383,285 million in fiscal year 2023.",
        )
    )
    return reg


def test_scenario_1_valid_citation_to_retrieved_evidence(sample_registry: EvidenceRegistry):
    """Scenario 1: Valid citation to retrieved evidence passes with 100% resolution."""
    answer = "Jensen Huang founded NVIDIA in 1993 and currently serves as CEO [G1]."
    result = validate_citations(answer, sample_registry)

    assert result.is_valid is True
    assert result.resolution_rate == 1.0
    assert result.valid_labels == ["[G1]"]
    assert result.invalid_labels == []
    assert len(result.resolved_citations) == 1
    assert result.resolved_citations[0].chunk_id == "chunk_nvda_graph_001"


def test_scenario_2_nonexistent_passage_id(sample_registry: EvidenceRegistry):
    """Scenario 2: Citation to a nonexistent passage ID ([P99]) is strictly rejected."""
    answer = "NVIDIA expanded its server ecosystem with partners [P99]."
    result = validate_citations(answer, sample_registry)

    assert result.is_valid is False
    assert "[P99]" in result.invalid_labels
    assert result.resolution_rate == 0.0
    assert "INVALID" in result.feedback_message
    assert "P99" in result.feedback_message


def test_scenario_3_real_passage_not_retrieved_for_current_request(
    sample_registry: EvidenceRegistry,
):
    """Scenario 3: Citation to a real corpus passage ID that was NOT retrieved for this request is rejected.

    Even if chunk_msft_099 exists in PostgreSQL, if it was not placed into this request's EvidenceRegistry,
    the model must not be allowed to fabricate a label for it.
    """
    # [P9] not in registry
    answer = "Microsoft reported cloud growth across Azure regions [P9]."
    result = validate_citations(answer, sample_registry)

    assert result.is_valid is False
    assert "[P9]" in result.invalid_labels
    assert "[P9]" not in sample_registry.get_valid_labels()


def test_scenario_4_citation_resolves_but_contradicts_claim(sample_registry: EvidenceRegistry):
    """Scenario 4: A citation resolves mechanically, but claim-support validation flags contradiction."""
    answer = "NVIDIA was founded in 2020 by Tim Cook [G1]."
    result = validate_citations(answer, sample_registry)

    # Mechanically resolves to chunk_nvda_graph_001
    assert result.is_valid is True
    assert len(result.resolved_citations) == 1

    # Simulate claim support check where evidence contradicts claim
    mock_decide = MagicMock()
    mock_decide.decide_claim_support.return_value = ("contradicts", 0.95)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("kgrag.answer.validator.get_decision_client", lambda: mock_decide)
        mp.setattr(
            "kgrag.answer.validator.get_settings",
            lambda: MagicMock(system_one=MagicMock(runtime="openrouter", api_key="test_key")),
        )
        checked = verify_claim_support(answer, result.resolved_citations)

    assert checked[0].supports_claim == "contradicts"
    assert checked[0].claim_support_confidence == 0.95


def test_scenario_5_material_factual_claim_without_citation(sample_registry: EvidenceRegistry):
    """Scenario 5: Answer containing material factual claims without citations is strictly rejected."""
    answer = "NVIDIA generated billions in revenue and bought Mellanox."
    result = validate_citations(answer, sample_registry)

    assert result.is_valid is False
    assert result.resolution_rate == 0.0
    assert "Your answer did not cite any evidence labels" in result.feedback_message


def test_scenario_6_malformed_citation_syntax(sample_registry: EvidenceRegistry):
    """Scenario 6: Malformed citation syntax (parens, space inside bracket, unbracketed) is caught."""
    # (G1) and [ G1 ] and [P-1] and [CHUNK_001]
    malformed_answer = "NVIDIA was founded in 1993 (G1) and bought Mellanox [ G1 ] or [CHUNK_001]."
    extracted = parse_citation_labels(malformed_answer)

    # Standard regex [GP]\d+ strictly excludes malformed strings
    assert "(G1)" not in extracted
    assert "[ G1 ]" not in extracted
    assert "[CHUNK_001]" not in extracted

    # When validated, since no valid bracketed labels were parsed, it fails with zero citations
    result = validate_citations(malformed_answer, sample_registry)
    assert result.is_valid is False
    assert result.resolution_rate == 0.0


def test_scenario_7_duplicate_citations_and_multiple_claims_sharing_evidence(
    sample_registry: EvidenceRegistry,
):
    """Scenario 7: Duplicate citations to the same evidence item are parsed in order and deduplicated in resolution."""
    answer = (
        "Jensen Huang is the CEO of NVIDIA [G1]. "
        "Under Huang's leadership [G1], NVIDIA acquired Mellanox [G2] and partnered on hardware [P1]."
    )
    result = validate_citations(answer, sample_registry)

    assert result.is_valid is True
    # Extracted list preserves raw citation sequence (3 mentions of G1/G2/P1)
    assert result.extracted_labels == ["[G1]", "[G1]", "[G2]", "[P1]"]
    # Unique resolved citations
    resolved_labels = [c.label for c in result.resolved_citations]
    assert resolved_labels == ["[G1]", "[G2]", "[P1]"]
    assert result.resolution_rate == 1.0


def test_scenario_8_graph_fact_missing_source_chunk_association():
    """Scenario 8: A graph fact registered without a valid chunk_id fails mechanical validation."""
    registry = EvidenceRegistry()
    # Malformed graph fact lacking chunk_id
    registry.register(
        EvidenceItem(
            label="[G1]",
            chunk_id="",  # Missing chunk provenance!
            text_snippet="Orphan graph fact with no source chunk",
        )
    )

    answer = "Orphan fact stated here [G1]."
    result = validate_citations(answer, registry)

    # Must be rejected because chunk_id is empty
    assert result.is_valid is False
    assert "[G1]" in result.invalid_labels
    assert result.resolution_rate == 0.0


def test_scenario_9_unregistered_model_hallucinated_labels(sample_registry: EvidenceRegistry):
    """Scenario 9: Model generating citation-like tokens ([G5], [Q1], [P42]) never in registry."""
    answer = (
        "NVIDIA was founded in 1993 [G1]. "
        "They also secretly developed quantum hyper-processors [G5] and partnered with SpaceX [P42]."
    )
    result = validate_citations(answer, sample_registry)

    assert result.is_valid is False
    assert "[G1]" in result.valid_labels
    assert "[G5]" in result.invalid_labels
    assert "[P42]" in result.invalid_labels
    assert result.resolution_rate == pytest.approx(1.0 / 3.0, 1e-4)
    assert "The following citation labels are INVALID" in result.feedback_message
