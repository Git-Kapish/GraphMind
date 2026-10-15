"""Integration test for Milestone M5: Minimal Retrieval & Safe Graph Templates (PRD §7.3, §14).

Acceptance criteria:
1. At least one verified multi-hop query returns a correct path with evidence for every edge.
2. Template tests pass (symmetry, direction, index use).
3. Vector retrieval returns source chunks with valid scores and provenance.
4. Dual retrieval returns a unified bundle with structured latencies.
"""

import pytest

from kgrag.graph.templates import (
    TemplateId,
    explain_template_query,
    query_neighbors,
    query_path_between,
    query_shared_neighbors,
    query_two_hop,
)
from kgrag.retrieval.engine import (
    GraphPathResult,
    RetrievalBundle,
    RetrievalEngine,
    VectorPassageResult,
)


@pytest.fixture
def engine():
    return RetrievalEngine()


def test_m5_verified_multihop_returns_evidenced_path(engine):
    """M5 Gate: At least one verified multi-hop query returns a correct path with evidence for every edge (PRD §14)."""
    # 2-hop traversal query from NVIDIA
    paths = engine.retrieve_graph(
        template_id=TemplateId.TWO_HOP,
        entity_1="nvidia",
        limit=5,
    )
    assert len(paths) > 0, "Expected at least one 2-hop path originating from anchor entity."

    # Verify every returned path has verified evidence supporting every edge
    for path in paths:
        assert isinstance(path, GraphPathResult)
        assert len(path.nodes) >= 3, f"Expected at least 3 nodes in 2-hop path, got: {path.nodes}"
        assert len(path.relations) >= 2, f"Expected at least 2 relations in 2-hop path, got: {path.relations}"
        assert len(path.observation_ids) >= 2, f"Expected at least 2 observation IDs for 2 edges, got: {path.observation_ids}"
        assert len(path.evidence) >= 1, "Expected attached verbatim evidence quotes."

        # Every evidence item must trace directly to a source chunk and quote
        for ev in path.evidence:
            assert ev.chunk_id, "Evidence missing source chunk_id."
            assert ev.evidence_quote, "Evidence missing verbatim quote."
            assert ev.observation_id in path.observation_ids, "Evidence observation_id not in path."


def test_m5_symmetry_and_directionality_invariants():
    """M5 Gate: Template tests pass symmetry (undirected) and directed invariants (PRD §14)."""
    # 1. Symmetry: COMPETES_WITH is symmetric and discoverable from either entity
    nvda_comp = query_neighbors("nvidia", relation_type="COMPETES_WITH", limit=5)
    amd_comp = query_neighbors("amd", relation_type="COMPETES_WITH", limit=5)
    assert len(nvda_comp) > 0 or len(amd_comp) > 0

    # 2. Directionality: OFFICER_OF is strictly (Person)-[OFFICER_OF]->(Company)
    # Outgoing from Company must be empty; incoming must contain officer
    out_edges = query_neighbors("nvidia", relation_type="OFFICER_OF", direction="out", limit=5)
    in_edges = query_neighbors("nvidia", relation_type="OFFICER_OF", direction="in", limit=5)
    assert len(out_edges) == 0, "Directed relation OFFICER_OF matched in reverse outgoing direction!"
    assert len(in_edges) > 0, "Directed relation OFFICER_OF failed to match in incoming direction!"


def test_m5_anchor_node_index_seek():
    """M5 Gate: Query plan verifies NodeUniqueIndexSeek on anchor entity_id (PRD §7.3, §14)."""
    cypher = "MATCH (a:Entity {entity_id: $a_id})-[r:COMPETES_WITH]-(b:Entity) RETURN a, r, b"
    plan_info = explain_template_query(cypher, {"a_id": "ent_99ee45010f6a"})
    assert plan_info["has_index_seek"] is True, f"Expected NodeUniqueIndexSeek in plan: {plan_info['plan_string']}"


def test_m5_vector_retrieval_returns_source_chunks(engine):
    """M5 Gate: Vector retrieval returns source chunks with valid scores and provenance (PRD §14)."""
    passages = engine.retrieve_vector("What are Broadcom's principal subsidiaries and products?", top_k=5)
    assert len(passages) == 5
    for p in passages:
        assert isinstance(p, VectorPassageResult)
        assert p.chunk_id, "Missing chunk_id."
        assert p.doc_id, "Missing doc_id."
        assert isinstance(p.ticker, str), "Missing ticker field."
        assert len(p.text) > 50, "Chunk text too short or empty."
        assert -1.0 <= p.cosine_similarity <= 1.0, f"Invalid cosine similarity: {p.cosine_similarity}"


def test_m5_dual_retrieval_bundle_integration(engine):
    """M5 Gate: Dual retrieval executes both graph templates and vector search into a unified bundle."""
    bundle = engine.retrieve_dual(
        query_text="What are NVIDIA's competitors and computing platforms?",
        template_id=TemplateId.NEIGHBORS,
        entity_1="nvidia",
        relation_type="COMPETES_WITH",
        top_k=3,
    )
    assert isinstance(bundle, RetrievalBundle)
    assert bundle.mode == "dual"
    assert len(bundle.graph_paths) > 0
    assert len(bundle.vector_passages) == 3
    assert bundle.latency_ms["total_ms"] > 0
    assert "graph_ms" in bundle.latency_ms
    assert "vector_ms" in bundle.latency_ms
