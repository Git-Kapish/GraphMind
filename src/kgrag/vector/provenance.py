"""Shared identifier helpers and bidirectional provenance mapping (PRD §7.2, FR-2.2, FR-2.4, Milestone M4)."""

import logging
from typing import Any

from kgrag.db.neo4j import get_session
from kgrag.db.postgres import get_connection
from kgrag.llm.client import get_llm_client

logger = logging.getLogger(__name__)


def sync_chunk_entity_ids() -> int:
    """Populate chunks.entity_ids by aggregating resolved entities from extraction_observations (PRD FR-2.1)."""
    update_sql = """
    UPDATE chunks c
    SET entity_ids = sub.eids
    FROM (
        SELECT
            chunk_id,
            ARRAY_AGG(DISTINCT eid) AS eids
        FROM (
            SELECT chunk_id, head_entity_id AS eid
            FROM extraction_observations
            WHERE resolution_status = 'resolved' AND head_entity_id IS NOT NULL
            UNION ALL
            SELECT chunk_id, tail_entity_id AS eid
            FROM extraction_observations
            WHERE resolution_status = 'resolved' AND tail_entity_id IS NOT NULL
        ) raw_eids
        GROUP BY chunk_id
    ) sub
    WHERE c.chunk_id = sub.chunk_id;
    """
    with get_connection(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(update_sql)
            cur.execute("SELECT count(*) AS cnt FROM chunks WHERE cardinality(entity_ids) > 0;")
            count = cur.fetchone()["cnt"]
    logger.info("Synchronized entity_ids across %d chunks.", count)
    return count


def observations_to_chunks(observation_ids: list[str]) -> list[dict[str, Any]]:
    """Direction 1: Map graph observation IDs to authoritative source chunks with filing metadata (PRD FR-2.2)."""
    if not observation_ids:
        return []

    sql = """
    SELECT DISTINCT
        c.chunk_id,
        c.doc_id,
        c.section_path,
        c.item,
        c.text,
        c.token_count,
        c.entity_ids,
        d.company,
        d.ticker,
        d.form_type,
        d.fiscal_year,
        d.filing_date,
        d.accession,
        d.source_url
    FROM extraction_observations o
    JOIN chunks c ON o.chunk_id = c.chunk_id
    JOIN documents d ON c.doc_id = d.doc_id
    WHERE o.observation_id = ANY(%(obs_ids)s);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"obs_ids": observation_ids})
            return cur.fetchall()


def graph_path_to_chunks(path_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Map a graph traversal path dict containing observation IDs to its supporting source chunks."""
    obs_ids = path_dict.get("observation_ids", [])
    for k in ("observations", "observations1", "observations2"):
        if k in path_dict and isinstance(path_dict[k], list):
            obs_ids.extend(path_dict[k])
    # Deduplicate observation IDs
    unique_obs_ids = list(dict.fromkeys(obs_ids))
    return observations_to_chunks(unique_obs_ids)


def chunk_to_graph_neighborhood(chunk_id: str) -> dict[str, Any]:
    """Direction 2: Map a source chunk to its extracted observations, entities, and Neo4j subgraph (PRD FR-2.2)."""
    # 1. Fetch observations originating from this chunk in PostgreSQL
    obs_sql = """
    SELECT
        observation_id,
        extraction_method,
        head_surface,
        head_type,
        head_entity_id,
        relation_type,
        tail_surface,
        tail_type,
        tail_entity_id,
        evidence_quote,
        resolution_status,
        evidence_verified
    FROM extraction_observations
    WHERE chunk_id = %(chunk_id)s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(obs_sql, {"chunk_id": chunk_id})
            observations = cur.fetchall()

    entity_ids = set()
    for o in observations:
        if o.get("head_entity_id"):
            entity_ids.add(o["head_entity_id"])
        if o.get("tail_entity_id"):
            entity_ids.add(o["tail_entity_id"])

    # 2. Query Neo4j for edges associated with this chunk or its entities
    neo4j_edges = []
    if entity_ids:
        with get_session() as session:
            query = """
            MATCH (h:Entity)-[r]->(t:Entity)
            WHERE $chunk_id IN r.source_chunks
               OR (h.entity_id IN $entity_ids AND t.entity_id IN $entity_ids)
            RETURN h.canonical_name AS source,
                   h.entity_id AS source_id,
                   type(r) AS relation,
                   t.canonical_name AS target,
                   t.entity_id AS target_id,
                   r.observation_ids AS observation_ids,
                   r.source_chunks AS source_chunks
            LIMIT 50;
            """
            res = session.run(query, chunk_id=chunk_id, entity_ids=list(entity_ids))
            neo4j_edges = [record.data() for record in res]

    return {
        "chunk_id": chunk_id,
        "observations_count": len(observations),
        "observations": observations,
        "connected_entity_ids": list(entity_ids),
        "graph_edges": neo4j_edges,
    }


def link_mention_to_entities(
    mention_text: str,
    top_k: int = 5,
    min_similarity: float = 0.40,
) -> list[dict[str, Any]]:
    """Hybrid entity linking using exact/alias matching followed by pgvector cosine distance (PRD FR-2.4, FR-3.2)."""
    from kgrag.resolve.normalizer import normalize_company_name

    norm_name = normalize_company_name(mention_text)

    # 1. Exact canonical or alias lookup in PostgreSQL
    exact_sql = """
    SELECT entity_id, canonical_name, type, aliases, 1.0 AS cosine_similarity, 'exact_or_alias' AS link_method
    FROM entities
    WHERE LOWER(canonical_name) = LOWER(%(norm)s)
       OR LOWER(canonical_name) = LOWER(%(raw)s)
       OR %(norm)s ILIKE ANY(aliases)
       OR %(raw)s ILIKE ANY(aliases)
    LIMIT %(top_k)s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(exact_sql, {"norm": norm_name, "raw": mention_text, "top_k": top_k})
            exact_matches = cur.fetchall()

    seen_ids = {r["entity_id"] for r in exact_matches}
    remaining_k = top_k - len(exact_matches)

    # 2. Dense vector embedding similarity
    vector_matches = []
    if remaining_k > 0:
        llm = get_llm_client()
        embs = llm.embed([mention_text])
        if embs:
            mention_vec = embs[0]
            sql = """
            SELECT
                entity_id,
                canonical_name,
                type,
                aliases,
                1 - (name_embedding <=> %(mention_vec)s::vector) AS cosine_similarity,
                'embedding_cosine' AS link_method
            FROM entities
            WHERE name_embedding IS NOT NULL
              AND NOT (entity_id = ANY(%(seen_ids)s))
            ORDER BY name_embedding <=> %(mention_vec)s::vector
            LIMIT %(top_k)s;
            """
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        {
                            "mention_vec": str(mention_vec),
                            "top_k": remaining_k,
                            "seen_ids": list(seen_ids) if seen_ids else ["none"],
                        },
                    )
                    vector_matches = [
                        r for r in cur.fetchall() if r["cosine_similarity"] >= min_similarity
                    ]

    return list(exact_matches) + list(vector_matches)


if __name__ == "__main__":
    sync_chunk_entity_ids()
