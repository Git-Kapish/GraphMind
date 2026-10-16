"""Unit tests for Context Assembly and Request-Scoped Evidence Registry (PRD §7.4, FR-4.2, Milestone M6)."""

from kgrag.answer.context import EvidenceRegistry, assemble_context
from kgrag.retrieval.engine import GraphEvidenceItem, GraphPathResult, VectorPassageResult


def test_evidence_registry_basic_operations():
    """Verify registry correctly stores, retrieves, and validates citation labels."""
    registry = EvidenceRegistry()
    assert len(registry) == 0

    from kgrag.answer.context import EvidenceItem

    item1 = EvidenceItem(
        label="[G1]", chunk_id="chk_01", text_snippet="NVIDIA partnered with Microsoft"
    )
    item2 = EvidenceItem(label="[P1]", chunk_id="chk_02", text_snippet="Passage text")

    registry.register(item1)
    registry.register(item2)

    assert len(registry) == 2
    assert registry.contains("[G1]") is True
    assert registry.contains("[P1]") is True
    assert registry.contains("[P99]") is False

    assert registry.get("[G1]").chunk_id == "chk_01"
    assert registry.get_valid_labels() == ["[G1]", "[P1]"]
    assert registry.get_chunk_ids() == {"chk_01", "chk_02"}


def test_assemble_context_with_dual_evidence():
    """Verify context assembly builds GRAPH FACTS and RETRIEVED PASSAGES with correct labels."""
    graph_paths = [
        GraphPathResult(
            template_id="neighbors",
            nodes=["NVIDIA", "Microsoft"],
            relations=["PARTNERS_WITH"],
            observation_ids=["obs_1"],
            evidence=[
                GraphEvidenceItem(
                    observation_id="obs_1",
                    chunk_id="chunk_sec_01",
                    evidence_quote="NVIDIA partnered with Microsoft to deploy HGX H100.",
                    relation_type="PARTNERS_WITH",
                    filing_company="NVIDIA CORP",
                    filing_ticker="NVDA",
                )
            ],
            metadata={"source": "NVIDIA", "target": "Microsoft", "relation": "PARTNERS_WITH"},
        )
    ]

    vector_passages = [
        VectorPassageResult(
            chunk_id="chunk_sec_02",
            doc_id="doc_01",
            company="NVIDIA CORP",
            ticker="NVDA",
            section_path="Item 1",
            text="NVIDIA accelerated computing platforms power AI data centers globally.",
            cosine_similarity=0.85,
        ),
        # Duplicate chunk to test deduplication
        VectorPassageResult(
            chunk_id="chunk_sec_02",
            doc_id="doc_01",
            company="NVIDIA CORP",
            ticker="NVDA",
            section_path="Item 1",
            text="NVIDIA accelerated computing platforms power AI data centers globally.",
            cosine_similarity=0.85,
        ),
    ]

    context_text, registry = assemble_context(
        graph_paths=graph_paths,
        vector_passages=vector_passages,
    )

    assert "### GRAPH FACTS" in context_text
    assert "### RETRIEVED PASSAGES" in context_text

    # Verify labels in text
    assert "[G1]" in context_text
    assert "[P1]" in context_text
    # Deduplication: [P2] must NOT exist because chunk_sec_02 was duplicated
    assert "[P2]" not in context_text

    # Verify registry mappings
    assert registry.contains("[G1]")
    assert registry.contains("[P1]")
    assert registry.get("[G1]").chunk_id == "chunk_sec_01"
    assert registry.get("[P1]").chunk_id == "chunk_sec_02"
    assert len(registry) == 2
