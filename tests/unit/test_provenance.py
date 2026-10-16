"""Unit tests for shared identifier helpers and bidirectional provenance mapping (PRD FR-2.2, FR-2.4, FR-2.5, Milestone M4)."""

from kgrag.vector.embeddings import validate_vector_dimensions
from kgrag.vector.provenance import (
    chunk_to_graph_neighborhood,
    graph_path_to_chunks,
    link_mention_to_entities,
    observations_to_chunks,
    sync_chunk_entity_ids,
)


def test_validate_vector_dimensions_success():
    """Verify that PostgreSQL vector columns match configured dimension (PRD FR-2.5)."""
    res = validate_vector_dimensions()
    assert res["status"] == "ok"
    assert res["dimension"] in (768, 2048)
    assert res["checked"] >= 2


def test_sync_chunk_entity_ids():
    """Verify that chunks.entity_ids is populated with resolved canonical entity IDs (PRD FR-2.1)."""
    count = sync_chunk_entity_ids()
    assert count > 0, "Expected at least 1 chunk with populated entity_ids"


def test_observations_to_chunks_mapping():
    """Verify mapping from observation IDs to authoritative source chunk metadata (PRD FR-2.2)."""
    from kgrag.db.postgres import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT observation_id, chunk_id FROM extraction_observations LIMIT 3;")
            rows = cur.fetchall()

    assert len(rows) > 0
    obs_ids = [r["observation_id"] for r in rows]
    chunks = observations_to_chunks(obs_ids)

    assert len(chunks) > 0
    first = chunks[0]
    assert "chunk_id" in first
    assert "doc_id" in first
    assert "text" in first
    assert "section_path" in first
    assert "company" in first
    assert "ticker" in first


def test_graph_path_to_chunks():
    """Verify extraction of supporting source chunks from a graph path dictionary."""
    from kgrag.db.postgres import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT observation_id FROM extraction_observations LIMIT 2;")
            rows = cur.fetchall()

    obs_ids = [r["observation_id"] for r in rows]
    mock_path = {
        "source": "AMD",
        "relation": "SUBSIDIARY_OF",
        "target": "Xilinx",
        "observation_ids": obs_ids,
    }

    chunks = graph_path_to_chunks(mock_path)
    assert len(chunks) > 0
    assert "chunk_id" in chunks[0]


def test_chunk_to_graph_neighborhood():
    """Verify mapping from source chunk to its extracted observations and Neo4j subgraph (PRD FR-2.2)."""
    from kgrag.db.postgres import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chunk_id
                FROM extraction_observations
                WHERE resolution_status = 'resolved'
                LIMIT 1;
                """
            )
            sample = cur.fetchone()

    chunk_id = sample["chunk_id"]
    neighborhood = chunk_to_graph_neighborhood(chunk_id)

    assert neighborhood["chunk_id"] == chunk_id
    assert neighborhood["observations_count"] > 0
    assert isinstance(neighborhood["observations"], list)
    assert isinstance(neighborhood["connected_entity_ids"], list)
    assert isinstance(neighborhood["graph_edges"], list)


def test_link_mention_to_entities_exact_and_alias():
    """Verify hybrid entity linking finds exact/alias matches with score 1.0 (PRD FR-2.4)."""
    # Exact canonical match
    res_nvda = link_mention_to_entities("NVIDIA Corporation", top_k=3)
    assert len(res_nvda) > 0
    assert any("nvidia" in r["canonical_name"].lower() for r in res_nvda)
    assert res_nvda[0]["cosine_similarity"] == 1.0
    assert res_nvda[0]["link_method"] == "exact_or_alias"

    # Known alias match
    res_tsmc = link_mention_to_entities("TSMC", top_k=3)
    assert len(res_tsmc) > 0
    assert any("taiwan semiconductor" in r["canonical_name"].lower() for r in res_tsmc)
    assert res_tsmc[0]["cosine_similarity"] == 1.0


def test_link_mention_to_entities_dense_embedding():
    """Verify dense vector embedding search on colloquial or descriptive person mentions (PRD FR-2.4)."""
    res_jensen = link_mention_to_entities("Jensen Huang", top_k=3, min_similarity=0.40)
    assert len(res_jensen) > 0
    assert any("jensen" in r["canonical_name"].lower() for r in res_jensen)
