"""Unit tests for structured LLMExtractor pipeline (PRD FR-1.3, FR-1.4)."""

import pytest

from kgrag.db.postgres import get_connection
from kgrag.extract.llm_extractor import LLMExtractor
from kgrag.extract.schemas import (
    EntityType,
    ExtractedRelation,
    ExtractionResult,
    RelationType,
)


class MockLLMClient:
    def __init__(self, return_result: ExtractionResult | None = None):
        self.model = "test-mock-model"
        self.return_result = return_result or ExtractionResult(chunk_id="test_mock", relations=[])
        self.call_count = 0

    def generate_structured(self, prompt: str, schema: type, **kwargs):
        self.call_count += 1
        return self.return_result


def test_extractor_prefilter_skip():
    mock_client = MockLLMClient()
    extractor = LLMExtractor(llm_client=mock_client)

    # Generic text that triggers no cues
    generic_text = (
        "Operating expenses increased slightly in the current fiscal year due to office leases."
    )
    results = extractor.extract_chunk(
        chunk_id="test_chunk_skip",
        chunk_text=generic_text,
        filer_company="Test Corp",
        filer_ticker="TST",
        force=True,
    )

    assert results == []
    # LLM should not have been invoked
    assert mock_client.call_count == 0


@pytest.fixture
def db_chunk_id():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT chunk_id FROM chunks LIMIT 1;")
            row = cur.fetchone()
            chunk_id = row["chunk_id"] if row else "test_chunk"

    yield chunk_id

    # Clean up any test observations inserted during tests
    with get_connection(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM extraction_observations WHERE model = 'test-mock-model';")
            cur.execute("DELETE FROM extraction_cache WHERE model = 'test-mock-model';")


def test_extractor_quote_verification_and_resolution(db_chunk_id):
    chunk_text = (
        "In 2024, our primary supplier was Taiwan Semiconductor Manufacturing Company (TSMC), "
        "which fabricated all of our high-end graphics processor dies."
    )
    mock_relations = [
        # Valid relation with exact quote and self-reference "our"
        ExtractedRelation(
            head_name="our",
            head_type=EntityType.COMPANY,
            relation=RelationType.MANUFACTURED_BY,
            tail_name="Taiwan Semiconductor Manufacturing Company",
            tail_type=EntityType.COMPANY,
            evidence_quote="our primary supplier was Taiwan Semiconductor Manufacturing Company (TSMC), which fabricated all of our high-end graphics processor dies",
            confidence=0.95,
        ),
        # Hallucinated relation not in text
        ExtractedRelation(
            head_name="Test Corp",
            head_type=EntityType.COMPANY,
            relation=RelationType.ACQUIRED,
            tail_name="Intel Corporation",
            tail_type=EntityType.COMPANY,
            evidence_quote="Test Corp acquired Intel Corporation in cash transaction.",
            confidence=0.99,
        ),
    ]

    mock_client = MockLLMClient(
        return_result=ExtractionResult(chunk_id=db_chunk_id, relations=mock_relations)
    )
    extractor = LLMExtractor(llm_client=mock_client)

    results = extractor.extract_chunk(
        chunk_id=db_chunk_id,
        chunk_text=chunk_text,
        filer_company="Test Corp",
        filer_ticker="TST",
        force=True,
    )

    assert mock_client.call_count == 1
    # Only 1 relation should be verified; hallucinated one rejected
    assert len(results) == 1
    rel = results[0]
    # Self reference resolved to filer
    assert rel["head_surface"] == "Test Corp"
    assert rel["tail_surface"] == "Taiwan Semiconductor Manufacturing Company"
    assert rel["relation_type"] == "MANUFACTURED_BY"
    assert rel["evidence_verified"] is True


def test_extractor_caching_behavior(db_chunk_id):
    chunk_text = (
        "We supply advanced networking silicon to Cisco Systems Inc. under long-term contract."
    )
    mock_relations = [
        ExtractedRelation(
            head_name="Test Corp",
            head_type=EntityType.COMPANY,
            relation=RelationType.SUPPLIES_TO,
            tail_name="Cisco Systems Inc.",
            tail_type=EntityType.COMPANY,
            evidence_quote="We supply advanced networking silicon to Cisco Systems Inc.",
            confidence=0.95,
        )
    ]
    mock_client = MockLLMClient(
        return_result=ExtractionResult(chunk_id=db_chunk_id, relations=mock_relations)
    )
    extractor = LLMExtractor(llm_client=mock_client)

    # First call - populates cache
    res1 = extractor.extract_chunk(
        chunk_id=db_chunk_id,
        chunk_text=chunk_text,
        filer_company="Test Corp",
        filer_ticker="TST",
        force=False,
    )
    assert mock_client.call_count == 1
    assert len(res1) == 1

    # Second call with force=False should hit cache and NOT invoke LLM again
    res2 = extractor.extract_chunk(
        chunk_id=db_chunk_id,
        chunk_text=chunk_text,
        filer_company="Test Corp",
        filer_ticker="TST",
        force=False,
    )
    assert mock_client.call_count == 1  # Unchanged!
    assert len(res2) == 1
    assert res2[0]["tail_surface"] == "Cisco Systems Inc."
