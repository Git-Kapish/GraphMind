"""Integration tests for graph projection integrity, provenance tracing, and rebuild idempotency (PRD FR-1.5, Milestone M3)."""

from kgrag.db.neo4j import get_session
from kgrag.db.postgres import get_connection
from kgrag.graph.rebuild import rebuild_graph_from_postgres


def test_rebuild_graph_concordance():
    """Verify that Neo4j projection precisely matches PostgreSQL authoritative counts."""
    # 1. Fetch expected counts from PostgreSQL
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS cnt FROM entities;")
            expected_entities = cur.fetchone()["cnt"]

            cur.execute(
                """
                SELECT count(*) AS cnt
                FROM (
                    SELECT head_entity_id, relation_type, tail_entity_id
                    FROM extraction_observations
                    WHERE resolution_status = 'resolved'
                      AND head_entity_id IS NOT NULL
                      AND tail_entity_id IS NOT NULL
                      AND head_entity_id <> tail_entity_id
                    GROUP BY head_entity_id, relation_type, tail_entity_id
                ) t;
                """
            )
            expected_edges = cur.fetchone()["cnt"]

    # 2. Run rebuild
    result = rebuild_graph_from_postgres()

    assert result["pg_entities"] == expected_entities
    assert result["pg_edges"] == expected_edges
    assert result["neo4j_nodes"] == expected_entities
    assert result["neo4j_edges"] == expected_edges


def test_rebuild_graph_idempotency():
    """Verify that executing rebuild twice consecutively yields identical node and edge counts."""
    res1 = rebuild_graph_from_postgres()
    res2 = rebuild_graph_from_postgres()

    assert res1["neo4j_nodes"] == res2["neo4j_nodes"]
    assert res1["neo4j_edges"] == res2["neo4j_edges"]
    assert res1["pg_entities"] == res2["pg_entities"]
    assert res1["pg_edges"] == res2["pg_edges"]


def test_graph_provenance_tracing():
    """Verify 100% mechanical provenance: Neo4j relationship -> PostgreSQL observation -> source chunk."""
    with get_session() as session:
        # Retrieve a sample relationship with its observation_ids
        record = session.run(
            """
            MATCH (h:Entity)-[r]->(t:Entity)
            WHERE size(r.observation_ids) > 0
            RETURN h.entity_id AS head_id,
                   h.canonical_name AS head_name,
                   type(r) AS rel_type,
                   t.entity_id AS tail_id,
                   t.canonical_name AS tail_name,
                   r.observation_ids AS obs_ids
            LIMIT 5;
            """
        ).data()

    assert len(record) > 0, "Expected at least 1 relationship in Neo4j with observation_ids"

    with get_connection() as conn:
        with conn.cursor() as cur:
            for edge in record:
                obs_ids = edge["obs_ids"]
                assert len(obs_ids) > 0

                # Verify each observation_id exists in extraction_observations
                cur.execute(
                    """
                    SELECT observation_id, chunk_id, evidence_quote, evidence_verified
                    FROM extraction_observations
                    WHERE observation_id = ANY(%s);
                    """,
                    (obs_ids,),
                )
                rows = cur.fetchall()
                assert len(rows) == len(obs_ids), f"Observation count mismatch for edge {edge}"

                # Verify each observation resolves to an actual chunk in PostgreSQL
                chunk_ids = [r["chunk_id"] for r in rows]
                cur.execute(
                    """
                    SELECT chunk_id, text, doc_id
                    FROM chunks
                    WHERE chunk_id = ANY(%s);
                    """,
                    (chunk_ids,),
                )
                chunk_rows = cur.fetchall()
                assert len(chunk_rows) > 0
                found_chunk_ids = {cr["chunk_id"] for cr in chunk_rows}
                for cid in chunk_ids:
                    assert cid in found_chunk_ids, (
                        f"Provenance broken: chunk_id {cid} missing from chunks table!"
                    )
