"""Query Router and Decision Logger (PRD §7.3 FR-3.1, §8, §9.1).

Responsible for:
1. Routing user questions to 'vector', 'graph', or 'hybrid' modes based on question intent and entity presence.
2. Mapping relational questions to parameterized safe Cypher templates (FR-3.2).
3. Enforcing fallback to 'hybrid' on low-confidence or ambiguous queries.
4. Logging every routing decision to the `routing_log` table in PostgreSQL.
"""

import logging
import re
import time
from typing import Any, Literal
from pydantic import BaseModel, Field

from kgrag.db.postgres import get_connection
from kgrag.graph.templates import TemplateId

logger = logging.getLogger(__name__)

# Keywords indicating relational / graph traversals
RELATIONAL_KEYWORDS = [
    "subsidiary", "subsidiaries", "own", "owns", "owned", "ownership",
    "parent", "affiliate", "exhibit 21", "officer", "officers", "ceo",
    "cfo", "executive", "executives", "director", "directors", "management",
    "leadership", "connect", "connected", "connection", "between",
    "path", "relate", "relationship", "how is", "how are", "shared",
    "both", "in common", "supplier", "customer", "partner", "acquire",
    "acquired", "merger", "how many", "count", "number of"
]

# Keywords indicating narrative / unstructured text search
NARRATIVE_KEYWORDS = [
    "risk", "risks", "item 1a", "competition", "competitive", "trends",
    "md&a", "item 7", "liquidity", "capital resources", "policy", "policies",
    "accounting", "discuss", "explain", "describe", "strategy", "factors",
    "overview", "business model", "outlook", "guidance", "inflation",
    "cybersecurity", "revenue recognition", "credit risk"
]


class RouteDecision(BaseModel):
    """Routing decision outcome with detected template and entities (PRD FR-3.1)."""
    chosen: Literal["vector", "graph", "hybrid"]
    confidence: float
    fallback_used: bool = False
    template_id: TemplateId | None = None
    entity_1: str | None = None
    entity_2: str | None = None
    relation_type: str | None = None
    relation_2: str | None = None
    detected_entities: list[str] = Field(default_factory=list)
    reasoning: str = ""


# In-memory entity and ticker cache for fast routing
_CACHED_ENTITIES: list[dict[str, Any]] | None = None
_CACHED_TICKERS: dict[str, str] | None = None
_CACHE_TIMESTAMP: float = 0.0
_CACHE_TTL_SECONDS: float = 300.0


def _get_entity_corpus() -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Retrieve cached entity and ticker mappings from PostgreSQL."""
    global _CACHED_ENTITIES, _CACHED_TICKERS, _CACHE_TIMESTAMP
    now = time.time()
    if _CACHED_ENTITIES is not None and (now - _CACHE_TIMESTAMP) < _CACHE_TTL_SECONDS:
        return _CACHED_ENTITIES, _CACHED_TICKERS or {}

    entities = []
    tickers = {}
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT entity_id, canonical_name, aliases FROM entities;")
                entities = list(cur.fetchall())

                cur.execute("SELECT DISTINCT ticker, company FROM documents WHERE ticker <> '';")
                for row in cur.fetchall():
                    if row["ticker"]:
                        tickers[row["ticker"].upper()] = row["company"]
        _CACHED_ENTITIES = entities
        _CACHED_TICKERS = tickers
        _CACHE_TIMESTAMP = now
    except Exception as e:
        logger.warning("Could not refresh entity corpus for router: %s", e)
        if _CACHED_ENTITIES is not None:
            return _CACHED_ENTITIES, _CACHED_TICKERS or {}

    return entities, tickers


def extract_entities_from_text(text: str) -> list[str]:
    """Extract candidate entity mentions from text using exact names, aliases, and ticker symbols."""
    entities, tickers = _get_entity_corpus()
    matched: set[str] = set()
    text_lower = text.lower()

    # 1. Match company ticker symbols as standalone words (e.g. \bNVDA\b, \bAMD\b)
    for ticker, company in tickers.items():
        if re.search(r"\b" + re.escape(ticker) + r"\b", text):
            matched.add(company)

    # 2. Match canonical entity names and aliases
    for e in entities:
        cname = e["canonical_name"]
        if len(cname) > 3 and cname.lower() in text_lower:
            matched.add(cname)
        for alias in (e["aliases"] or []):
            if len(alias) > 3 and alias.lower() in text_lower:
                matched.add(cname)

    # 3. Discard shorter substring duplicates (e.g., prefer 'NVIDIA Corporation' over 'nvidia')
    sorted_matches = sorted(matched, key=len, reverse=True)
    final_matches: list[str] = []
    for m in sorted_matches:
        if not any(m.lower() in existing.lower() for existing in final_matches):
            final_matches.append(m)

    return final_matches


def infer_template_and_params(
    question: str,
    entities: list[str],
) -> tuple[TemplateId | None, str | None, str | None, str | None]:
    q_lower = question.lower()

    # Prioritize specific entities over generic filers if multiple entities are detected
    PARENT_FILERS = {
        "nvidia", "nvidia corp", "nvidia corporation", "intel", "intel corp",
        "intel corporation", "broadcom", "broadcom inc.", "microsoft",
        "microsoft corp", "microsoft corporation", "micron", "micron technology",
        "micron technology inc", "advanced micro devices", "advanced micro devices inc",
        "amd", "advanced micro devices sdn. bhd"
    }
    ordered_entities = list(entities)
    if len(ordered_entities) >= 2:
        if ordered_entities[0].lower() in PARENT_FILERS and ordered_entities[1].lower() not in PARENT_FILERS:
            ordered_entities = [ordered_entities[1], ordered_entities[0]] + ordered_entities[2:]

    e1 = ordered_entities[0] if len(ordered_entities) >= 1 else None
    e2 = ordered_entities[1] if len(ordered_entities) >= 2 else None

    # Officers query pattern
    if any(k in q_lower for k in ["officer", "officers", "ceo", "cfo", "executive", "executives", "directors", "management", "leadership"]):
        if e1:
            return TemplateId.OFFICERS_OF, e1, None, None

    # Shared neighbors / connections in common
    if any(k in q_lower for k in ["shared", "both", "in common", "common"]):
        if e1 and e2:
            return TemplateId.SHARED_NEIGHBORS, e1, e2, None
        if e1:
            return TemplateId.NEIGHBORS, e1, None, None

    # Path between two entities
    if any(k in q_lower for k in ["path", "connected", "connection", "between", "relate", "relationship", "how is", "how are"]):
        if e1 and e2:
            return TemplateId.PATH_BETWEEN, e1, e2, None
        if e1:
            return TemplateId.NEIGHBORS, e1, None, None

    # Count of relationships (use word boundaries to avoid matching 'country')
    if any(re.search(r"\b" + re.escape(k) + r"\b", q_lower) for k in ["how many", "count", "number of", "total count"]):
        if e1:
            rel = "SUBSIDIARY_OF" if any(s in q_lower for s in ["subsidiary", "subsidiaries", "company", "companies"]) else "EXECUTIVE_OFFICER_OF"
            return TemplateId.COUNT_BY_RELATION, e1, None, rel

    # Top connected / hubs
    if any(k in q_lower for k in ["most connected", "top connected", "hub", "highest degree"]):
        return TemplateId.TOP_CONNECTED, None, None, None

    # Subsidiaries / jurisdiction / ownership
    if any(k in q_lower for k in ["subsidiary", "subsidiaries", "own", "owns", "owned", "parent", "jurisdiction", "operate", "operates"]):
        if e1:
            return TemplateId.NEIGHBORS, e1, None, None

    # Default if 1 entity detected
    if e1:
        return TemplateId.NEIGHBORS, e1, None, None

    return None, None, None, None


def route_query(
    question: str,
    mode: Literal["auto", "vector", "graph", "hybrid"] = "auto",
) -> RouteDecision:
    """Analyze query and route to vector, graph, or hybrid retrieval path (PRD FR-3.1)."""
    detected_entities = extract_entities_from_text(question)
    template_id, entity_1, entity_2, relation_type = infer_template_and_params(question, detected_entities)

    q_lower = question.lower()
    has_relational = any(k in q_lower for k in RELATIONAL_KEYWORDS)
    has_narrative = any(k in q_lower for k in NARRATIVE_KEYWORDS)

    # 1. Explicit override modes
    if mode == "vector":
        return RouteDecision(
            chosen="vector",
            confidence=1.0,
            fallback_used=False,
            detected_entities=detected_entities,
            reasoning="Explicit vector mode requested by client.",
        )
    if mode == "graph":
        return RouteDecision(
            chosen="graph",
            confidence=1.0,
            fallback_used=False,
            template_id=template_id,
            entity_1=entity_1,
            entity_2=entity_2,
            relation_type=relation_type,
            detected_entities=detected_entities,
            reasoning="Explicit graph mode requested by client.",
        )
    if mode == "hybrid":
        return RouteDecision(
            chosen="hybrid",
            confidence=1.0,
            fallback_used=False,
            template_id=template_id,
            entity_1=entity_1,
            entity_2=entity_2,
            relation_type=relation_type,
            detected_entities=detected_entities,
            reasoning="Explicit hybrid mode requested by client.",
        )

    # 2. Automated routing (mode == "auto")
    # Case A: Clear relational query with matched entity
    if has_relational and detected_entities and not has_narrative:
        # If pure structure (e.g. officers, path, count)
        if template_id in (TemplateId.OFFICERS_OF, TemplateId.PATH_BETWEEN, TemplateId.COUNT_BY_RELATION, TemplateId.SHARED_NEIGHBORS):
            return RouteDecision(
                chosen="graph",
                confidence=0.88,
                fallback_used=False,
                template_id=template_id,
                entity_1=entity_1,
                entity_2=entity_2,
                relation_type=relation_type,
                detected_entities=detected_entities,
                reasoning=f"Identified high-confidence relational template {template_id.value} for {entity_1}.",
            )
        # General relational question
        return RouteDecision(
            chosen="hybrid",
            confidence=0.85,
            fallback_used=False,
            template_id=template_id,
            entity_1=entity_1,
            entity_2=entity_2,
            relation_type=relation_type,
            detected_entities=detected_entities,
            reasoning=f"Relational intent with text context needed; routed to hybrid using {template_id.value if template_id else 'none'}.",
        )

    # Case B: Clear narrative / risk / textual disclosure query with no or secondary entities
    if has_narrative and not has_relational:
        return RouteDecision(
            chosen="vector",
            confidence=0.88,
            fallback_used=False,
            detected_entities=detected_entities,
            reasoning="Narrative disclosure / risk factor query routed to vector semantic search.",
        )

    # Case C: Both narrative and relational aspects present -> hybrid
    if has_relational and has_narrative:
        return RouteDecision(
            chosen="hybrid",
            confidence=0.82,
            fallback_used=False,
            template_id=template_id,
            entity_1=entity_1,
            entity_2=entity_2,
            relation_type=relation_type,
            detected_entities=detected_entities,
            reasoning="Query combines relational relationships and narrative descriptions; routed to hybrid.",
        )

    # Case D: Entity detected without clear relational keyword
    if detected_entities:
        return RouteDecision(
            chosen="hybrid",
            confidence=0.75,
            fallback_used=False,
            template_id=template_id,
            entity_1=entity_1,
            entity_2=entity_2,
            relation_type=relation_type,
            detected_entities=detected_entities,
            reasoning=f"Entity '{entity_1}' detected; dual hybrid search dispatched.",
        )

    # Case E: Ambiguous / generic question with no entity match
    # Low confidence triggers hybrid retrieval with fallback_used=True (PRD FR-3.1)
    return RouteDecision(
        chosen="hybrid",
        confidence=0.60,
        fallback_used=True,
        template_id=None,
        detected_entities=[],
        reasoning="Low routing confidence; falling back to hybrid retrieval per PRD FR-3.1.",
    )


def log_routing_decision(
    question: str,
    route: str,
    confidence: float,
    fallback_used: bool,
    outcome: str,
    latency_ms: int,
    request_id: str,
) -> None:
    """Log every routing decision to PostgreSQL routing_log (PRD §8, §9.1)."""
    insert_sql = """
    INSERT INTO routing_log (question, route, confidence, fallback_used, outcome, latency_ms, request_id)
    VALUES (%(question)s, %(route)s, %(confidence)s, %(fallback_used)s, %(outcome)s, %(latency_ms)s, %(request_id)s);
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    insert_sql,
                    {
                        "question": question,
                        "route": route,
                        "confidence": float(confidence),
                        "fallback_used": bool(fallback_used),
                        "outcome": outcome[:64],
                        "latency_ms": int(latency_ms),
                        "request_id": str(request_id),
                    },
                )
    except Exception as e:
        logger.warning("Failed to record routing decision into routing_log: %s", e)
