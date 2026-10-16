"""Unit tests for configuration and ontology loading (PRD §13, FR-1.1)."""

from kgrag.config import get_ontology, get_prefilter_config, get_settings


def test_settings_loaded():
    settings = get_settings()
    assert settings.embedding.dimension in (768, 2048)
    assert settings.llm.runtime in ("openrouter", "ollama")
    assert settings.query.default_top_k == 8
    assert settings.extraction.confidence_floor == 0.5
    assert settings.extraction.max_extraction_chunks == 800
    assert settings.query.runtime_support_check is False


def test_ontology_entities_and_relations():
    ontology = get_ontology()
    entity_names = [e["name"] for e in ontology.get("entity_types", [])]
    expected_entities = [
        "Company",
        "Person",
        "Product",
        "Technology",
        "Market",
        "Location",
        "Regulation",
    ]
    for expected in expected_entities:
        assert expected in entity_names

    rel_map = {r["name"]: r for r in ontology.get("relationship_types", [])}
    assert "SUBSIDIARY_OF" in rel_map
    assert "OFFICER_OF" in rel_map

    # PRD FR-1.1: PARTNERS_WITH and COMPETES_WITH must be symmetric
    assert rel_map["PARTNERS_WITH"].get("symmetric") is True
    assert rel_map["COMPETES_WITH"].get("symmetric") is True
    # SUBSIDIARY_OF and SUPPLIES_TO must NOT be symmetric
    assert rel_map["SUBSIDIARY_OF"].get("symmetric") is False
    assert rel_map["SUPPLIES_TO"].get("symmetric") is False


def test_prefilter_cues_and_gazetteer():
    prefilter = get_prefilter_config()
    cues = prefilter.get("relation_cues", [])
    assert "supplier" in cues
    assert "subsidiar" in cues
    assert "acquir" in cues

    gazetteer = prefilter.get("gazetteer", {})
    assert gazetteer.get("min_entity_mentions") == 2
    seed_entities = gazetteer.get("seed_entities", [])
    assert len(seed_entities) > 0
