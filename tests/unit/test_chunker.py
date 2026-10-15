"""Unit tests for section-aware chunker (PRD FR-1.2)."""

from kgrag.data.chunker import SectionChunker, estimate_tokens
from kgrag.data.sec_parser import SectionContent


def test_chunk_tokens_and_stable_ids():
    chunker = SectionChunker(target_tokens=100, overlap_tokens=20, min_tokens=50, max_tokens=150)
    accession = "0001045810-26-000021"
    sample_text = (
        "Paragraph one discusses semiconductor architectures and hardware accelerator units.\n\n"
        "Paragraph two outlines manufacturing processes with foundry partners across East Asia.\n\n"
        "Paragraph three covers software platform layers, CUDA libraries, and developer tools.\n\n"
        "Paragraph four describes customer data center deployments and hyperscaler cloud services."
    )
    sec = SectionContent(
        item="item1",
        section_name="Item 1. Business",
        text=sample_text,
        char_count=len(sample_text),
        sha256="fake_sha256",
    )

    chunks = chunker.chunk_section(accession, sec)
    assert len(chunks) > 0

    # Test stable ID format: {accession}:{item}:{idx:04d}
    for idx, c in enumerate(chunks):
        assert c.chunk_id == f"{accession}:item1:{idx:04d}"
        assert c.doc_id == accession
        assert c.item == "item1"
        assert c.token_count > 0

    # Repeat chunking to verify deterministic idempotency
    chunks_repeat = chunker.chunk_section(accession, sec)
    assert [c.chunk_id for c in chunks] == [c.chunk_id for c in chunks_repeat]
    assert [c.text for c in chunks] == [c.text for c in chunks_repeat]


def test_estimate_tokens():
    text = "NVIDIA Corporation designs graphics processing units and system on a chip units."
    tokens = estimate_tokens(text)
    assert tokens >= 10
