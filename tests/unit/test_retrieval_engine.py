"""Unit tests for Dual Minimal Retrieval Engine (PRD §7.3, Milestone M5)."""

import pytest

from kgrag.graph.templates import TemplateId
from kgrag.retrieval.engine import (
    GraphPathResult,
    RetrievalBundle,
    RetrievalEngine,
    VectorPassageResult,
)


@pytest.fixture
def engine():
    return RetrievalEngine()


def test_engine_retrieve_graph_neighbors(engine):
    """Verify graph retrieval via NEIGHBORS template returns structured paths and evidence."""
    paths = engine.retrieve_graph(TemplateId.NEIGHBORS, entity_1="nvidia", limit=3)
    assert len(paths) > 0
    assert isinstance(paths[0], GraphPathResult)
    assert paths[0].template_id == "neighbors"
    assert len(paths[0].nodes) >= 2


def test_engine_retrieve_graph_shared_neighbors(engine):
    """Verify 2-hop shared neighbor path retrieval."""
    paths = engine.retrieve_graph(
        TemplateId.SHARED_NEIGHBORS, entity_1="nvidia", entity_2="microsoft", limit=3
    )
    assert len(paths) > 0
    assert paths[0].template_id == "shared_neighbors"
    assert len(paths[0].nodes) >= 3


def test_engine_retrieve_vector(engine):
    """Verify vector retrieval returns top-k passages with similarity and metadata."""
    passages = engine.retrieve_vector("What are NVIDIA's accelerated computing products?", top_k=3)
    assert len(passages) == 3
    assert isinstance(passages[0], VectorPassageResult)
    assert passages[0].cosine_similarity > 0.0
    assert len(passages[0].text) > 0
    assert passages[0].ticker is not None


def test_engine_retrieve_dual(engine):
    """Verify unified dual retrieval produces a RetrievalBundle with both graph paths and passages."""
    bundle = engine.retrieve_dual(
        query_text="What are AMD's primary subsidiaries and products?",
        template_id=TemplateId.NEIGHBORS,
        entity_1="AMD",
        relation_type="SUBSIDIARY_OF",
        top_k=3,
    )

    assert isinstance(bundle, RetrievalBundle)
    assert bundle.mode == "dual"
    assert len(bundle.graph_paths) > 0
    assert len(bundle.vector_passages) > 0
    assert "graph_ms" in bundle.latency_ms
    assert "vector_ms" in bundle.latency_ms
    assert "total_ms" in bundle.latency_ms
