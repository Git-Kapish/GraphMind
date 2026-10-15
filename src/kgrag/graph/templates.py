"""Safe, Parameterized Cypher Query Templates and Evidence Attachment (PRD §7.3, FR-3.2, Milestone M5)."""

from enum import Enum
import logging
import re
from typing import Any

from neo4j import Session

from kgrag.config import get_ontology, get_settings
from kgrag.db.neo4j import get_session
from kgrag.db.postgres import get_connection

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TemplateId(str, Enum):
    """Closed enumeration of safe, pre-written parameterized Cypher query templates (PRD FR-3.2)."""
    NEIGHBORS = "neighbors"
    TWO_HOP = "two_hop"
    PATH_BETWEEN = "path_between"
    SHARED_NEIGHBORS = "shared_neighbors"
    COUNT_BY_RELATION = "count_by_relation"
    TOP_CONNECTED = "top_connected"
    OFFICERS_OF = "officers_of"


class StrictResolutionStatus(str, Enum):
    """Status outcomes for entity mention linking policy (PRD FR-3.2)."""
    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    NEEDS_CLARIFICATION = "needs_clarification"


class EntityResolutionResult(BaseModel):
    """Structured result of linking an entity mention to the knowledge graph (PRD FR-3.2)."""
    status: StrictResolutionStatus
    entity_id: str | None = None
    canonical_name: str | None = None
    confidence: float = 0.0
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    message: str = ""


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


def validate_relation_type(relation_type: str | None) -> str | None:
    """Validate relation type against closed ontology enum to prevent arbitrary query injection."""
    if not relation_type:
        return None
    cleaned = relation_type.strip().upper()
    if cleaned not in ALLOWED_RELATIONS:
        # Coerce punctuation / whitespace
        coerced = re.sub(r"[^A-Z0-9_]", "_", cleaned)
        if coerced in ALLOWED_RELATIONS:
            return coerced
        raise ValueError(f"Invalid relation type '{relation_type}'. Must be one of: {sorted(ALLOWED_RELATIONS)}")
    return cleaned


def map_to_canonical_entity_id(entity_id: str) -> tuple[str, str | None]:
    """Map entity ID through merge history to its surviving canonical ID and name (PRD FR-1.4, FR-3.2)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT h.canonical_entity_id, e.canonical_name
                FROM entity_merge_history h
                LEFT JOIN entities e ON h.canonical_entity_id = e.entity_id
                WHERE h.source_entity_id = %(id)s
                  AND h.decision = 'auto_merged'
                ORDER BY h.id DESC
                LIMIT 1;
                """,
                {"id": entity_id},
            )
            row = cur.fetchone()
            if row and row["canonical_entity_id"]:
                return row["canonical_entity_id"], row["canonical_name"]
    return entity_id, None


def resolve_entity_strict(mention: str) -> EntityResolutionResult:
    """Resolve entity mention using exact/alias first, then similarity, rejecting ambiguity (PRD FR-3.2).

    Rules:
    1. Exact canonical or alias matches resolve unambiguously.
    2. Dense vector candidates in the review band or with near ties return needs_clarification.
    3. Candidates below review threshold or with zero matches return not_found.
    4. Never guesses.
    """
    if not mention or not mention.strip():
        return EntityResolutionResult(
            status=StrictResolutionStatus.NOT_FOUND,
            message="Entity mention cannot be empty.",
        )

    settings = get_settings()
    from kgrag.vector.provenance import link_mention_to_entities

    candidates = link_mention_to_entities(mention.strip(), top_k=5)
    if not candidates:
        return EntityResolutionResult(
            status=StrictResolutionStatus.NOT_FOUND,
            message=f"Entity '{mention}' not found in knowledge graph.",
        )

    exact_matches = [c for c in candidates if c.get("link_method") == "exact_or_alias"]
    if exact_matches:
        # Map all matched IDs through merge history to their surviving canonical entity
        canonical_id_map: dict[str, tuple[str, str]] = {}
        for c in exact_matches:
            cid, cname = map_to_canonical_entity_id(c["entity_id"])
            canonical_id_map[c["entity_id"]] = (cid, cname or c["canonical_name"])

        unique_cids = {cid for cid, _ in canonical_id_map.values()}
        if len(unique_cids) == 1:
            canonical_eid = list(unique_cids)[0]
            canonical_cname = list(canonical_id_map.values())[0][1]
            return EntityResolutionResult(
                status=StrictResolutionStatus.RESOLVED,
                entity_id=canonical_eid,
                canonical_name=canonical_cname,
                confidence=1.0,
                candidates=exact_matches,
                message=f"Resolved via exact match: {canonical_cname}",
            )
        return EntityResolutionResult(
            status=StrictResolutionStatus.NEEDS_CLARIFICATION,
            candidates=exact_matches,
            message=f"Ambiguous exact matches for '{mention}'. Multiple entities matched.",
        )

    # Check vector similarity candidates
    top = candidates[0]
    top_sim = float(top.get("cosine_similarity", 0.0))

    if top_sim < settings.resolution.review_band_lower:
        return EntityResolutionResult(
            status=StrictResolutionStatus.NOT_FOUND,
            candidates=candidates,
            confidence=top_sim,
            message=f"No candidate met the minimum similarity threshold ({top_sim:.3f} < {settings.resolution.review_band_lower}).",
        )

    if top_sim < settings.resolution.embedding_similarity_threshold:
        return EntityResolutionResult(
            status=StrictResolutionStatus.NEEDS_CLARIFICATION,
            candidates=candidates,
            confidence=top_sim,
            message=f"Candidate '{top['canonical_name']}' is in the review band ({top_sim:.3f}). Needs clarification.",
        )

    # Check margin with second candidate to detect close ambiguity
    if len(candidates) > 1:
        second = candidates[1]
        second_sim = float(second.get("cosine_similarity", 0.0))
        if (top_sim - second_sim < 0.03) and (top["entity_id"] != second["entity_id"]):
            return EntityResolutionResult(
                status=StrictResolutionStatus.NEEDS_CLARIFICATION,
                candidates=candidates[:2],
                confidence=top_sim,
                message=f"Ambiguous candidates: '{top['canonical_name']}' ({top_sim:.3f}) vs '{second['canonical_name']}' ({second_sim:.3f}).",
            )

    cid, cname = map_to_canonical_entity_id(top["entity_id"])
    return EntityResolutionResult(
        status=StrictResolutionStatus.RESOLVED,
        entity_id=cid,
        canonical_name=cname or top["canonical_name"],
        confidence=top_sim,
        candidates=candidates,
        message=f"Resolved via embedding similarity: {cname or top['canonical_name']}",
    )


def resolve_anchor_entity_id(entity_id_or_name: str) -> tuple[str, str]:
    """Resolve an input entity ID or name to its canonical entity_id and canonical_name."""
    if not entity_id_or_name:
        raise ValueError("Entity ID or name must not be empty.")

    # 1. Direct entity_id check in PostgreSQL
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT entity_id, canonical_name
                FROM entities
                WHERE entity_id = %(id)s;
                """,
                {"id": entity_id_or_name},
            )
            row = cur.fetchone()
            if row:
                cid, cname = map_to_canonical_entity_id(row["entity_id"])
                return cid, cname or row["canonical_name"]

            # 2. Strict entity resolution (exact match, alias, ticker, or high-confidence embedding)
            strict_res = resolve_entity_strict(entity_id_or_name)
            if strict_res.status == StrictResolutionStatus.RESOLVED and strict_res.entity_id:
                return strict_res.entity_id, strict_res.canonical_name or entity_id_or_name

            # 3. Fuzzy ILIKE containment match fallback
            cur.execute(
                """
                SELECT entity_id, canonical_name
                FROM entities
                WHERE canonical_name ILIKE %(pattern)s
                ORDER BY length(canonical_name) ASC
                LIMIT 1;
                """,
                {"pattern": f"%{entity_id_or_name.strip()}%"},
            )
            row = cur.fetchone()
            if row:
                cid, cname = map_to_canonical_entity_id(row["entity_id"])
                return cid, cname or row["canonical_name"]

    # Fallback to deterministic ID if not yet in database
    from kgrag.resolve.resolver import normalize_name
    canon, eid = normalize_name(entity_id_or_name)
    cid, cname = map_to_canonical_entity_id(eid)
    return cid, cname or canon


# ---------------------------------------------------------------------------
# TEMPLATE 1: NEIGHBORS (1-Hop Entities Linked to X by Relation R)
# ---------------------------------------------------------------------------
def query_neighbors(
    entity_id_or_name: str,
    relation_type: str | None = None,
    direction: str = "both",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve 1-hop connected neighbors for an anchor entity (PRD FR-3.2)."""
    settings = get_settings()
    hard_limit = min(limit, settings.query.graph_path_hard_limit)
    eid, canon_name = resolve_anchor_entity_id(entity_id_or_name)
    rel = validate_relation_type(relation_type)

    if rel:
        if rel in SYMMETRIC_RELATIONS or direction == "both":
            pattern = f"-[r:{rel}]-"
        elif direction == "in":
            pattern = f"<-[r:{rel}]-"
        else:
            pattern = f"-[r:{rel}]->"
    else:
        pattern = "-[r]-"

    cypher = f"""
    MATCH (a:Entity {{entity_id: $a_id}}){pattern}(b:Entity)
    WHERE b.entity_id <> a.entity_id
    RETURN a.canonical_name AS source,
           a.entity_id AS source_id,
           type(r) AS relation,
           b.canonical_name AS target,
           b.entity_id AS target_id,
           b.type AS target_type,
           r.observation_ids AS observation_ids,
           r.source_chunks AS source_chunks,
           r.weight AS weight
    LIMIT $limit;
    """

    with get_session() as session:
        res = session.run(
            cypher,
            a_id=eid,
            limit=hard_limit,
            timeout=settings.query.graph_path_timeout_seconds,
        )
        return [record.data() for record in res]


# ---------------------------------------------------------------------------
# TEMPLATE 2: TWO_HOP (X -> ? -> ? under Selected Relation Types)
# ---------------------------------------------------------------------------
def query_two_hop(
    entity_id_or_name: str,
    relation_1: str | None = None,
    relation_2: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve 2-hop traversal paths originating from an anchor entity without node repeats (PRD FR-3.2)."""
    settings = get_settings()
    hard_limit = min(limit, settings.query.graph_path_hard_limit)
    eid, _ = resolve_anchor_entity_id(entity_id_or_name)
    r1 = validate_relation_type(relation_1)
    r2 = validate_relation_type(relation_2)

    pat1 = f"-[r1:{r1}]-" if (r1 in SYMMETRIC_RELATIONS) else (f"-[r1:{r1}]->" if r1 else "-[r1]-")
    pat2 = f"-[r2:{r2}]-" if (r2 in SYMMETRIC_RELATIONS) else (f"-[r2:{r2}]->" if r2 else "-[r2]-")

    cypher = f"""
    MATCH (a:Entity {{entity_id: $a_id}}){pat1}(m:Entity){pat2}(b:Entity)
    WHERE m.entity_id <> a.entity_id
      AND b.entity_id <> a.entity_id
      AND b.entity_id <> m.entity_id
    RETURN a.canonical_name AS source,
           a.entity_id AS source_id,
           type(r1) AS relation_1,
           m.canonical_name AS intermediate,
           m.entity_id AS intermediate_id,
           m.type AS intermediate_type,
           type(r2) AS relation_2,
           b.canonical_name AS target,
           b.entity_id AS target_id,
           b.type AS target_type,
           r1.observation_ids + r2.observation_ids AS observation_ids,
           r1.source_chunks + r2.source_chunks AS source_chunks
    LIMIT $limit;
    """

    with get_session() as session:
        res = session.run(
            cypher,
            a_id=eid,
            limit=hard_limit,
            timeout=settings.query.graph_path_timeout_seconds,
        )
        return [record.data() for record in res]


# ---------------------------------------------------------------------------
# TEMPLATE 3: PATH_BETWEEN (Bounded Paths Between A and B; Max 3 Hops)
# ---------------------------------------------------------------------------
def query_path_between(
    entity_1: str,
    entity_2: str,
    max_hops: int = 3,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find bounded shortest paths between two entities up to max_hops (max 3, PRD FR-3.2)."""
    settings = get_settings()
    hard_limit = min(limit, settings.query.graph_path_hard_limit)
    safe_hops = min(max_hops, 3)

    eid1, _ = resolve_anchor_entity_id(entity_1)
    eid2, _ = resolve_anchor_entity_id(entity_2)

    cypher = f"""
    MATCH p = shortestPath((a:Entity {{entity_id: $a_id}})-[*1..{safe_hops}]-(b:Entity {{entity_id: $b_id}}))
    WHERE a.entity_id <> b.entity_id
    RETURN [n in nodes(p) | n.canonical_name] AS path_nodes,
           [n in nodes(p) | n.entity_id] AS path_entity_ids,
           [rel in relationships(p) | type(rel)] AS path_relations,
           reduce(acc = [], rel in relationships(p) | acc + rel.observation_ids) AS observation_ids,
           reduce(acc = [], rel in relationships(p) | acc + rel.source_chunks) AS source_chunks,
           length(p) AS hop_count
    LIMIT $limit;
    """

    with get_session() as session:
        res = session.run(
            cypher,
            a_id=eid1,
            b_id=eid2,
            limit=hard_limit,
            timeout=settings.query.graph_path_timeout_seconds,
        )
        return [record.data() for record in res]


# ---------------------------------------------------------------------------
# TEMPLATE 4: SHARED_NEIGHBORS (Entities Connected to Both A and B)
# ---------------------------------------------------------------------------
def query_shared_neighbors(
    entity_1: str,
    entity_2: str,
    relation_type: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Find intermediate entities linked to both entity A and entity B (PRD FR-3.2)."""
    settings = get_settings()
    hard_limit = min(limit, settings.query.graph_path_hard_limit)
    eid1, _ = resolve_anchor_entity_id(entity_1)
    eid2, _ = resolve_anchor_entity_id(entity_2)
    rel = validate_relation_type(relation_type)

    pat1 = f"-[r1:{rel}]-" if rel else "-[r1]-"
    pat2 = f"-[r2:{rel}]-" if rel else "-[r2]-"

    cypher = f"""
    MATCH (a:Entity {{entity_id: $a_id}}){pat1}(m:Entity){pat2}(b:Entity {{entity_id: $b_id}})
    WHERE a.entity_id <> b.entity_id
      AND m.entity_id <> a.entity_id
      AND m.entity_id <> b.entity_id
    RETURN a.canonical_name AS entity_1,
           a.entity_id AS entity_1_id,
           type(r1) AS relation_1,
           m.canonical_name AS shared_entity,
           m.entity_id AS shared_entity_id,
           m.type AS shared_entity_type,
           type(r2) AS relation_2,
           b.canonical_name AS entity_2,
           b.entity_id AS entity_2_id,
           r1.observation_ids + r2.observation_ids AS observation_ids,
           r1.source_chunks + r2.source_chunks AS source_chunks
    LIMIT $limit;
    """

    with get_session() as session:
        res = session.run(
            cypher,
            a_id=eid1,
            b_id=eid2,
            limit=hard_limit,
            timeout=settings.query.graph_path_timeout_seconds,
        )
        return [record.data() for record in res]


# ---------------------------------------------------------------------------
# TEMPLATE 5: COUNT_BY_RELATION (Count Unique Entities Connected via R)
# ---------------------------------------------------------------------------
def query_count_by_relation(
    entity_id_or_name: str,
    relation_type: str,
) -> dict[str, Any]:
    """Count unique canonical entities connected to X via relation R (PRD FR-3.2)."""
    settings = get_settings()
    eid, canon_name = resolve_anchor_entity_id(entity_id_or_name)
    rel = validate_relation_type(relation_type)
    if not rel:
        raise ValueError("Relation type is required for count_by_relation template.")

    cypher = f"""
    MATCH (a:Entity {{entity_id: $a_id}})-[r:{rel}]-(b:Entity)
    WHERE b.entity_id <> a.entity_id
    RETURN a.canonical_name AS entity,
           a.entity_id AS entity_id,
           $rel AS relation,
           count(DISTINCT b) AS entity_count,
           collect(DISTINCT b.canonical_name)[0..10] AS sample_entities,
           reduce(acc = [], rel in collect(r) | acc + rel.observation_ids)[0..20] AS observation_ids;
    """

    with get_session() as session:
        res = session.run(
            cypher,
            a_id=eid,
            rel=rel,
            timeout=settings.query.graph_path_timeout_seconds,
        )
        record = res.single()
        return record.data() if record else {
            "entity": canon_name,
            "entity_id": eid,
            "relation": rel,
            "entity_count": 0,
            "sample_entities": [],
            "observation_ids": [],
        }


# ---------------------------------------------------------------------------
# TEMPLATE 6: TOP_CONNECTED (Rank Entities by Degree under Relation)
# ---------------------------------------------------------------------------
def query_top_connected(
    relation_type: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Rank entities by degree under a specified relation or overall graph connectivity (PRD FR-3.2)."""
    settings = get_settings()
    hard_limit = min(limit, settings.query.graph_path_hard_limit)
    rel = validate_relation_type(relation_type)

    rel_pattern = f":{rel}" if rel else ""

    cypher = f"""
    MATCH (a:Entity)-[r{rel_pattern}]-(b:Entity)
    WHERE a.entity_id <> b.entity_id
    RETURN a.canonical_name AS entity,
           a.entity_id AS entity_id,
           a.type AS entity_type,
           count(DISTINCT b) AS degree,
           collect(DISTINCT b.canonical_name)[0..5] AS sample_connections
    ORDER BY degree DESC
    LIMIT $limit;
    """

    with get_session() as session:
        res = session.run(
            cypher,
            limit=hard_limit,
            timeout=settings.query.graph_path_timeout_seconds,
        )
        return [record.data() for record in res]


# ---------------------------------------------------------------------------
# TEMPLATE 7: OFFICERS_OF (Executive Officers Evidenced at Company)
# ---------------------------------------------------------------------------
def query_officers_of(
    company_id_or_name: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve individuals with an explicitly evidenced OFFICER_OF relationship to a company (PRD FR-3.2)."""
    settings = get_settings()
    hard_limit = min(limit, settings.query.graph_path_hard_limit)
    cid, company_name = resolve_anchor_entity_id(company_id_or_name)

    cypher = """
    MATCH (p:Entity)-[r:OFFICER_OF]->(c:Entity {entity_id: $c_id})
    RETURN p.canonical_name AS officer_name,
           p.entity_id AS officer_id,
           p.type AS officer_type,
           c.canonical_name AS company_name,
           c.entity_id AS company_id,
           r.observation_ids AS observation_ids,
           r.source_chunks AS source_chunks
    LIMIT $limit;
    """

    with get_session() as session:
        res = session.run(
            cypher,
            c_id=cid,
            limit=hard_limit,
            timeout=settings.query.graph_path_timeout_seconds,
        )
        return [record.data() for record in res]


# ---------------------------------------------------------------------------
# EVIDENCE ATTACHMENT & EXPLAIN PLAN INSPECTION
# ---------------------------------------------------------------------------
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
        c.section_path,
        d.company AS filing_company,
        d.ticker AS filing_ticker
    FROM extraction_observations o
    JOIN chunks c ON o.chunk_id = c.chunk_id
    JOIN documents d ON c.doc_id = d.doc_id
    WHERE o.observation_id = ANY(%(obs_ids)s);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"obs_ids": list(set(observation_ids))})
            return cur.fetchall()


def attach_evidence_to_paths(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach resolved verbatim evidence quotes and source chunks to returned graph paths."""
    all_obs_ids = []
    for p in paths:
        obs_ids = p.get("observation_ids", [])
        if obs_ids:
            all_obs_ids.extend(obs_ids)

    evidence_by_id = {
        row["observation_id"]: row
        for row in fetch_evidence_for_observations(all_obs_ids)
    }

    enriched_paths = []
    for p in paths:
        p_copy = dict(p)
        path_obs = p.get("observation_ids", [])
        p_copy["evidence"] = [evidence_by_id[oid] for oid in path_obs if oid in evidence_by_id]
        enriched_paths.append(p_copy)

    return enriched_paths


def explain_template_query(cypher: str, params: dict[str, Any]) -> dict[str, Any]:
    """Execute EXPLAIN on parameterized Cypher query to verify index seek on anchor node (PRD FR-3.2)."""
    with get_session() as session:
        res = session.run(f"EXPLAIN {cypher}", **params)
        summary = res.consume()
        plan_str = summary.plan.get("args", {}).get("string-representation", "") if summary.plan else ""
        return {
            "plan": summary.plan,
            "plan_string": plan_str,
            "has_index_seek": "NodeUniqueIndexSeek" in plan_str or "NodeIndexSeek" in plan_str,
        }
