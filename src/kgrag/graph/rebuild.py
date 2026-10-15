"""Idempotent Neo4j Graph Rebuild from PostgreSQL Observations (PRD §9.1, Milestone M3/M2.5)."""

import logging
import time
from typing import Any

from kgrag.db.neo4j import get_session, init_constraints
from kgrag.db.postgres import get_connection
from kgrag.graph.writer import upsert_edges_batch, upsert_entities_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def rebuild_graph_from_postgres() -> dict[str, Any]:
    """Reconstruct Neo4j graph completely from authoritative PostgreSQL tables."""
    start_time = time.perf_counter()
    logger.info("Starting idempotent Neo4j graph rebuild...")

    # 1. Ensure constraints exist
    init_constraints()

    # 2. Fetch canonical entities from PostgreSQL
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT entity_id, canonical_name, type, aliases FROM entities;")
            entities = cur.fetchall()

            # Fetch resolved edges aggregated from extraction_observations
            cur.execute(
                """
                SELECT
                    head_entity_id,
                    relation_type,
                    tail_entity_id,
                    array_agg(observation_id) AS observation_ids,
                    array_agg(DISTINCT chunk_id) AS source_chunks,
                    count(*) AS weight
                FROM extraction_observations
                WHERE resolution_status = 'resolved'
                  AND head_entity_id IS NOT NULL
                  AND tail_entity_id IS NOT NULL
                  AND head_entity_id <> tail_entity_id
                GROUP BY head_entity_id, relation_type, tail_entity_id;
                """
            )
            edges = cur.fetchall()

    logger.info(
        "Fetched %d entities and %d aggregated edges from PostgreSQL.",
        len(entities),
        len(edges),
    )

    # 3. Project into Neo4j
    with get_session() as session:
        # Clear existing nodes and relationships
        logger.info("Clearing existing Neo4j graph...")
        session.run("MATCH (n) DETACH DELETE n;")

        # Upsert entities
        logger.info("Upserting :Entity nodes...")
        num_nodes = upsert_entities_batch(session, entities)

        # Upsert relationships
        logger.info("Upserting relationships...")
        num_edges = upsert_edges_batch(session, edges)

        # Read back Neo4j verification counts
        neo4j_nodes = session.run("MATCH (n:Entity) RETURN count(n) AS cnt").single()["cnt"]
        neo4j_edges = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]

    elapsed = time.perf_counter() - start_time
    logger.info(
        "Neo4j graph rebuild complete in %.2fs: %d nodes, %d edges.",
        elapsed,
        neo4j_nodes,
        neo4j_edges,
    )

    print("\n" + "=" * 65)
    print("  NEO4J GRAPH REBUILD SUMMARY (PRD §9.1)")
    print("=" * 65)
    print(f"- PostgreSQL Entities Ingested:       {len(entities)}")
    print(f"- PostgreSQL Aggregated Edges:        {len(edges)}")
    print(f"- Neo4j :Entity Nodes Projected:      {neo4j_nodes}")
    print(f"- Neo4j Relationships Projected:      {neo4j_edges}")
    print(f"- Rebuild Elapsed Time:               {elapsed:.2f}s")
    print("=" * 65 + "\n")

    return {
        "pg_entities": len(entities),
        "pg_edges": len(edges),
        "neo4j_nodes": neo4j_nodes,
        "neo4j_edges": neo4j_edges,
        "elapsed_seconds": elapsed,
    }


if __name__ == "__main__":
    rebuild_graph_from_postgres()
