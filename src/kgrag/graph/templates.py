"""Parameterized Cypher query templates and evidence fetcher (PRD §10, Milestone M2.5/M5)."""

import logging
from typing import Any

from kgrag.db.neo4j import get_session
from kgrag.db.postgres import get_connection

logger = logging.getLogger(__name__)


def query_neighbors(
    entity_name: str,
    relation_type: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve 1-hop connected neighbors for an entity."""
    with get_session() as session:
        if relation_type:
            # Undirected match so direction doesn't block discovery
            cypher = f"""
            MATCH (e:Entity)-[r:{relation_type}]-(target:Entity)
            WHERE toLower(e.canonical_name) CONTAINS toLower($name)
               OR ANY(alias IN e.aliases WHERE toLower(alias) CONTAINS toLower($name))
            RETURN e.canonical_name AS source,
                   type(r) AS relation,
                   target.canonical_name AS target,
                   target.type AS target_type,
                   r.observation_ids AS observation_ids,
                   r.source_chunks AS source_chunks
            LIMIT $limit;
            """
        else:
            cypher = """
            MATCH (e:Entity)-[r]-(target:Entity)
            WHERE toLower(e.canonical_name) CONTAINS toLower($name)
               OR ANY(alias IN e.aliases WHERE toLower(alias) CONTAINS toLower($name))
            RETURN e.canonical_name AS source,
                   type(r) AS relation,
                   target.canonical_name AS target,
                   target.type AS target_type,
                   r.observation_ids AS observation_ids,
                   r.source_chunks AS source_chunks
            LIMIT $limit;
            """
        res = session.run(cypher, name=entity_name, limit=limit)
        return [record.data() for record in res]


def query_shared_neighbors(
    entity_name_1: str,
    entity_name_2: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find entities connected to both entity 1 and entity 2 (2-hop common neighbor pattern)."""
    cypher = """
    MATCH (e1:Entity)-[r1]-(mid:Entity)-[r2]-(e2:Entity)
    WHERE (toLower(e1.canonical_name) CONTAINS toLower($name1) OR ANY(a IN e1.aliases WHERE toLower(a) CONTAINS toLower($name1)))
      AND (toLower(e2.canonical_name) CONTAINS toLower($name2) OR ANY(a IN e2.aliases WHERE toLower(a) CONTAINS toLower($name2)))
      AND e1 <> e2 AND e1 <> mid AND e2 <> mid
    RETURN e1.canonical_name AS entity_1,
           type(r1) AS relation_1,
           mid.canonical_name AS shared_entity,
           mid.type AS shared_entity_type,
           type(r2) AS relation_2,
           e2.canonical_name AS entity_2,
           r1.observation_ids + r2.observation_ids AS observation_ids,
           r1.source_chunks + r2.source_chunks AS source_chunks
    LIMIT $limit;
    """
    with get_session() as session:
        res = session.run(cypher, name1=entity_name_1, name2=entity_name_2, limit=limit)
        return [record.data() for record in res]


def query_two_hop(
    entity_name: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve 2-hop traversal paths originating from an entity."""
    cypher = """
    MATCH (e1:Entity)-[r1]-(mid:Entity)-[r2]-(e2:Entity)
    WHERE (toLower(e1.canonical_name) CONTAINS toLower($name) OR ANY(a IN e1.aliases WHERE toLower(a) CONTAINS toLower($name)))
      AND e1 <> e2 AND e1 <> mid AND e2 <> mid
    RETURN e1.canonical_name AS source,
           type(r1) AS relation_1,
           mid.canonical_name AS intermediate,
           type(r2) AS relation_2,
           e2.canonical_name AS target,
           e2.type AS target_type,
           r1.observation_ids + r2.observation_ids AS observation_ids,
           r1.source_chunks + r2.source_chunks AS source_chunks
    LIMIT $limit;
    """
    with get_session() as session:
        res = session.run(cypher, name=entity_name, limit=limit)
        return [record.data() for record in res]


def query_path_between(
    entity_name_1: str,
    entity_name_2: str,
    max_hops: int = 3,
) -> list[dict[str, Any]]:
    """Find shortest path between two entities up to max_hops."""
    cypher = f"""
    MATCH p = shortestPath((e1:Entity)-[*1..{max_hops}]-(e2:Entity))
    WHERE (toLower(e1.canonical_name) CONTAINS toLower($name1) OR ANY(a IN e1.aliases WHERE toLower(a) CONTAINS toLower($name1)))
      AND (toLower(e2.canonical_name) CONTAINS toLower($name2) OR ANY(a IN e2.aliases WHERE toLower(a) CONTAINS toLower($name2)))
      AND e1 <> e2
    RETURN [node in nodes(p) | node.canonical_name] AS path_nodes,
           [rel in relationships(p) | type(rel)] AS path_relations,
           reduce(acc = [], rel in relationships(p) | acc + rel.observation_ids) AS observation_ids,
           reduce(acc = [], rel in relationships(p) | acc + rel.source_chunks) AS source_chunks,
           length(p) AS hop_count
    LIMIT 1;
    """
    with get_session() as session:
        res = session.run(cypher, name1=entity_name_1, name2=entity_name_2)
        record = res.single()
        return [record.data()] if record else []


def fetch_evidence_for_observations(observation_ids: list[str]) -> list[dict[str, Any]]:
    """Fetch verbatim evidence quotes and chunk metadata from PostgreSQL for observation IDs."""
    if not observation_ids:
        return []

    sql = """
    SELECT
        o.observation_id,
        o.chunk_id,
        o.head_surface,
        o.relation_type,
        o.tail_surface,
        o.evidence_quote,
        c.item,
        d.company AS filing_company,
        d.ticker AS filing_ticker
    FROM extraction_observations o
    JOIN chunks c ON o.chunk_id = c.chunk_id
    JOIN documents d ON c.doc_id = d.doc_id
    WHERE o.observation_id = ANY(%(obs_ids)s);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"obs_ids": observation_ids})
            return cur.fetchall()
