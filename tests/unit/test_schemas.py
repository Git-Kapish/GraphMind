"""Unit tests for Pydantic extraction schemas and coercion rules (PRD FR-1.1, FR-1.3)."""

from kgrag.extract.schemas import (
    EntityType,
    ExtractedRelation,
    ExtractionResult,
    RelationType,
)


def test_extracted_relation_valid():
    rel = ExtractedRelation(
        head_name="Intel Corporation",
        head_type=EntityType.COMPANY,
        relation=RelationType.SUPPLIES_TO,
        tail_name="Cisco Systems, Inc.",
        tail_type=EntityType.COMPANY,
        evidence_quote="Intel supplies packaging services to Cisco Systems.",
        confidence=0.95,
    )
    assert rel.head_name == "Intel Corporation"
    assert rel.relation == RelationType.SUPPLIES_TO
    assert rel.confidence == 0.95


def test_extracted_relation_auto_coercion():
    raw_data = {
        "head_name": "NVIDIA",
        "head_type": "company",  # lowercase string
        "relation": "manufactured_by",  # lowercase string
        "tail_name": "TSMC",
        "tail_type": "company",  # lowercase string
        "evidence_quote": "TSMC manufactures NVIDIA chips.",
        "confidence": 0.9,
    }
    rel = ExtractedRelation.model_validate(raw_data)
    assert rel.relation == RelationType.MANUFACTURED_BY
    assert rel.head_type == EntityType.COMPANY
    assert rel.tail_type == EntityType.COMPANY


def test_extracted_relation_defaults_missing_types():
    raw_data = {
        "head_name": "Jensen Huang",
        "relation": "OFFICER_OF",
        "tail_name": "NVIDIA Corporation",
        "evidence_quote": "Jensen Huang serves as CEO of NVIDIA Corporation.",
    }
    rel = ExtractedRelation.model_validate(raw_data)
    assert rel.head_type == EntityType.PERSON
    assert rel.tail_type == EntityType.COMPANY
    assert rel.confidence == 0.9  # Default confidence


def test_extraction_result_empty():
    result = ExtractionResult(chunk_id="chunk_123", relations=[])
    assert result.chunk_id == "chunk_123"
    assert len(result.relations) == 0


def test_extraction_result_with_relations():
    data = {
        "chunk_id": "chunk_456",
        "relations": [
            {
                "head_name": "AMD",
                "head_type": "Company",
                "relation": "COMPETES_WITH",
                "tail_name": "Intel",
                "tail_type": "Company",
                "evidence_quote": "AMD competes directly with Intel in the x86 microprocessor market.",
                "confidence": 0.98,
            }
        ],
    }
    result = ExtractionResult.model_validate(data)
    assert len(result.relations) == 1
    assert result.relations[0].tail_name == "Intel"
