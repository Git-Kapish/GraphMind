"""Neo4j graph writer with idempotent MERGE and symmetric relation handling (PRD §9.2)."""

import logging
import re
from typing import Any

from neo4j import Session

logger = logging.getLogger(__name__)

# Valid ontology relation types
ALLOWED_RELATIONS: set[str] = {
    "SUBSIDIARY_OF",
    "ACQUIRED",
    "INVESTS_IN",
    "PARTNERS_WITH",
    "SUPPLIES_TO",
    "MANUFACTURED_BY",
    "COMPETES_WITH",
    "OFFERS",
    "BUILT_ON",
    "COMPETES_IN",
    "OPERATES_IN",
    "SUBJECT_TO",
    "OFFICER_OF",
    "HEADQUARTERED_IN",
}

SYMMETRIC_RELATIONS: set[str] = {"PARTNERS_WITH", "COMPETES_WITH"}


def upsert_entities_batch(
    session: Session, entities: list[dict[str, Any]], batch_size: int = 500
) -> int:
    """Batch upsert :Entity nodes into Neo4j."""
    query = """
    UNWIND $batch AS item
    MERGE (e:Entity {entity_id: item.entity_id})
    SET e.canonical_name = item.canonical_name,
        e.type = item.type,
        e.aliases = item.aliases
    """
    total = 0
    for i in range(0, len(entities), batch_size):
        chunk = entities[i : i + batch_size]
        session.run(query, batch=chunk)
        total += len(chunk)
    return total


def upsert_edges_batch(session: Session, edges: list[dict[str, Any]], batch_size: int = 500) -> int:
    """Batch upsert relationships into Neo4j, grouping by relation type."""
    # Group edges by relation type
    grouped: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        rel_type = edge["relation_type"].strip().upper()
        if rel_type not in ALLOWED_RELATIONS:
            # Coerce common variants
            rel_type = re.sub(r"[^A-Z0-9_]", "_", rel_type)
            if rel_type not in ALLOWED_RELATIONS:
                continue

        head_id = edge["head_entity_id"]
        tail_id = edge["tail_entity_id"]

        # For symmetric relations, enforce canonical endpoint ordering
        if rel_type in SYMMETRIC_RELATIONS:
            if head_id > tail_id:
                head_id, tail_id = tail_id, head_id

        payload = {
            "head_id": head_id,
            "tail_id": tail_id,
            "obs_ids": edge.get("observation_ids", []),
            "chunks": edge.get("source_chunks", []),
            "weight": edge.get("weight", len(edge.get("observation_ids", []))),
        }
        grouped.setdefault(rel_type, []).append(payload)

    total_edges = 0
    for rel_type, rel_edges in grouped.items():
        # Parameterized query with sanitized relation type from closed ontology
        query = f"""
        UNWIND $batch AS item
        MATCH (h:Entity {{entity_id: item.head_id}})
        MATCH (t:Entity {{entity_id: item.tail_id}})
        MERGE (h)-[r:{rel_type}]->(t)
        SET r.observation_ids = item.obs_ids,
            r.source_chunks = item.chunks,
            r.weight = item.weight
        """
        for i in range(0, len(rel_edges), batch_size):
            chunk = rel_edges[i : i + batch_size]
            session.run(query, batch=chunk)
            total_edges += len(chunk)

    return total_edges
