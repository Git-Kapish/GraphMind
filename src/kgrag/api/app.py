"""FastAPI application for Knowledge Graph RAG (PRD §8, Milestone M7).

Exposes:
- POST /query: Auto-routed or mode-specified hybrid/graph/vector query answering with citation invariants.
- POST /query/baseline: Plain vector RAG baseline query endpoint for fair A/B comparison.
- GET /entities/{entity_id}: Canonical entity details, merge provenance, and graph relationships.
- GET /chunks/{chunk_id}: Authoritative chunk text, SEC document metadata, and extraction observations.
- GET /health: Component reachability health check without leaking secrets.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from kgrag import __version__
from kgrag.answer.context import assemble_context
from kgrag.answer.generator import generate_grounded_answer
from kgrag.api.models import (
    ChunkDetailResponse,
    ChunkObservationItem,
    CitationItem,
    ComponentHealth,
    EntityDetailResponse,
    HealthResponse,
    LatencyBreakdown,
    QueryRequest,
    QueryResponse,
    RouteInfo,
    ValidationResult,
)
from kgrag.db import neo4j as neo4j_db
from kgrag.db import postgres as pg_db
from kgrag.graph.templates import StrictResolutionStatus, resolve_entity_strict
from kgrag.llm.client import close_llm_client, get_llm_client
from kgrag.retrieval.engine import GraphPathResult, RetrievalEngine, VectorPassageResult
from kgrag.retrieval.router import log_routing_decision, route_query

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database schemas and constraints on startup."""
    logger.info("Initializing Knowledge Graph RAG service...")
    try:
        pg_db.init_schema()
    except Exception as e:
        logger.warning("Could not auto-initialize PostgreSQL schema at startup: %s", e)

    try:
        neo4j_db.init_constraints()
    except Exception as e:
        logger.warning("Could not auto-initialize Neo4j constraints at startup: %s", e)

    yield

    logger.info("Shutting down Knowledge Graph RAG service...")
    neo4j_db.close_driver()
    close_llm_client()


app = FastAPI(
    title="Knowledge Graph RAG API",
    description="Local-first hybrid Knowledge Graph & Vector RAG over enterprise 10-K filings",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global retrieval engine instance and dependency provider
engine = RetrievalEngine()


def get_engine() -> RetrievalEngine:
    """Dependency injection provider for RetrievalEngine."""
    return engine


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Component reachability health check without leaking secrets (PRD §8)."""
    pg_health = pg_db.check_health()
    neo4j_health = neo4j_db.check_health()
    llm_health = get_llm_client().check_health()

    components = {
        "postgres": ComponentHealth(
            status=pg_health.get("status", "unknown"),
            details={"pgvector_installed": pg_health.get("pgvector_installed", False)},
        ),
        "neo4j": ComponentHealth(
            status=neo4j_health.get("status", "unknown"),
            details={"edition": neo4j_health.get("edition", "unknown")},
        ),
        "llm": ComponentHealth(
            status=llm_health.get("status", "unknown"),
            details={
                "target_model": llm_health.get("target_model", ""),
                "model_available": llm_health.get("model_available", False),
            },
        ),
    }

    all_healthy = all(c.status == "healthy" for c in components.values())
    any_healthy = any(c.status == "healthy" for c in components.values())
    overall_status = "ok" if all_healthy else ("degraded" if any_healthy else "unhealthy")

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(UTC).isoformat(),
        version=__version__,
        components=components,
    )


@app.post("/query", response_model=QueryResponse)
def query_endpoint(
    req: QueryRequest,
    retrieval_engine: RetrievalEngine = Depends(get_engine),
) -> QueryResponse:
    """End-to-end grounded query endpoint with auto/explicit routing and citation resolution (PRD §8)."""
    t0 = time.perf_counter()
    request_id = str(uuid.uuid4())

    # 1. Routing decision
    t_route_0 = time.perf_counter()
    decision = route_query(question=req.question, mode=req.mode)
    t_route = int((time.perf_counter() - t_route_0) * 1000)

    # 2. Ambiguity check on primary detected entity (PRD FR-4.5)
    if decision.entity_1:
        strict_res = resolve_entity_strict(decision.entity_1)
        if strict_res.status == StrictResolutionStatus.NEEDS_CLARIFICATION:
            t_total = int((time.perf_counter() - t0) * 1000)
            log_routing_decision(
                question=req.question,
                route=decision.chosen,
                confidence=decision.confidence,
                fallback_used=decision.fallback_used,
                outcome="needs_clarification",
                latency_ms=t_total,
                request_id=request_id,
            )
            return QueryResponse(
                answer=f"Entity mention '{decision.entity_1}' is ambiguous. Please clarify which entity you mean.",
                citations=[],
                route=RouteInfo(
                    chosen=decision.chosen,
                    confidence=decision.confidence,
                    fallback_used=decision.fallback_used,
                ),
                graph_paths=[],
                passages=[],
                validation=ValidationResult(
                    citation_resolution_passed=True,
                    claim_support_status="not_evaluated",
                    attempts=1,
                ),
                status="needs_clarification",
                latency_ms=LatencyBreakdown(route=t_route, retrieve=0, generate=0, total=t_total),
                request_id=request_id,
            )

    # 3. Retrieval Execution
    t_ret_0 = time.perf_counter()
    graph_paths: list[GraphPathResult] = []
    vector_passages: list[VectorPassageResult] = []
    fallback_used = decision.fallback_used

    if decision.chosen == "vector":
        vector_passages = retrieval_engine.retrieve_vector(req.question, top_k=req.top_k)
    elif decision.chosen == "graph":
        if decision.template_id and decision.entity_1:
            try:
                graph_paths = retrieval_engine.retrieve_graph(
                    template_id=decision.template_id,
                    entity_1=decision.entity_1,
                    entity_2=decision.entity_2,
                    relation_type=decision.relation_type,
                    relation_2=decision.relation_2,
                    limit=req.top_k,
                )
            except Exception as e:
                logger.warning("Graph template query failed: %s", e)

        # If auto mode selected graph but no paths found, fall back to vector retrieval (PRD FR-3.1)
        if not graph_paths and req.mode == "auto":
            logger.info("Graph path returned 0 results in auto mode; falling back to vector retrieval.")
            vector_passages = retrieval_engine.retrieve_vector(req.question, top_k=req.top_k)
            fallback_used = True
    else:  # hybrid
        if decision.template_id and decision.entity_1:
            try:
                graph_paths = retrieval_engine.retrieve_graph(
                    template_id=decision.template_id,
                    entity_1=decision.entity_1,
                    entity_2=decision.entity_2,
                    relation_type=decision.relation_type,
                    relation_2=decision.relation_2,
                    limit=req.top_k,
                )
            except Exception as e:
                logger.warning("Graph template query failed in hybrid mode: %s", e)
        vector_passages = retrieval_engine.retrieve_vector(req.question, top_k=req.top_k)

    t_ret = int((time.perf_counter() - t_ret_0) * 1000)

    # 4. Context Assembly
    context_text, registry = assemble_context(
        graph_paths=graph_paths,
        vector_passages=vector_passages,
    )

    # 5. Check evidence availability (PRD FR-4.5 Refusal)
    if not graph_paths and not vector_passages:
        t_total = int((time.perf_counter() - t0) * 1000)
        log_routing_decision(
            question=req.question,
            route=decision.chosen,
            confidence=decision.confidence,
            fallback_used=fallback_used,
            outcome="refused",
            latency_ms=t_total,
            request_id=request_id,
        )
        return QueryResponse(
            answer="No relevant evidence was found in the SEC filings to answer this question.",
            citations=[],
            route=RouteInfo(
                chosen=decision.chosen,
                confidence=decision.confidence,
                fallback_used=fallback_used,
            ),
            graph_paths=[],
            passages=[],
            validation=ValidationResult(
                citation_resolution_passed=True,
                claim_support_status="not_evaluated",
                attempts=1,
            ),
            status="refused",
            latency_ms=LatencyBreakdown(route=t_route, retrieve=t_ret, generate=0, total=t_total),
            request_id=request_id,
        )

    # 6. Grounded Generation & Mechanical Citation Invariant Validation
    t_gen_0 = time.perf_counter()
    outcome = generate_grounded_answer(
        question=req.question,
        context_text=context_text,
        registry=registry,
        max_retries=2,
    )
    t_gen = int((time.perf_counter() - t_gen_0) * 1000)
    t_total = int((time.perf_counter() - t0) * 1000)

    # Map citations to schema
    citation_items = [
        CitationItem(
            label=c.label.strip("[]"),
            chunk_id=c.chunk_id,
            doc=c.doc_id or c.company or "SEC 10-K",
            section=c.section_path or "Filing",
            snippet=c.evidence_quote or (c.text_snippet[:200] if c.text_snippet else ""),
            supports_claim="unknown",
        )
        for c in outcome.citations
    ]

    # Map response status
    resp_status: Any = "ok"
    if outcome.status == "refusal":
        resp_status = "refused"
    elif outcome.status == "needs_clarification":
        resp_status = "needs_clarification"
    elif outcome.status == "validation_failed":
        resp_status = "validation_failed"

    # Log routing and outcome to PostgreSQL routing_log (PRD §8, §9.1)
    log_routing_decision(
        question=req.question,
        route=decision.chosen,
        confidence=decision.confidence,
        fallback_used=fallback_used,
        outcome=resp_status,
        latency_ms=t_total,
        request_id=request_id,
    )

    # Debug payload handling
    debug_graph_paths: list[dict[str, Any]] = []
    debug_passages: list[dict[str, Any]] = []
    if req.debug:
        debug_graph_paths = [gp.model_dump() for gp in graph_paths]
        debug_passages = [vp.model_dump() for vp in vector_passages]

    citation_passed = outcome.resolution_rate >= 1.0 if outcome.citations else (outcome.status in ("refusal", "needs_clarification"))

    return QueryResponse(
        answer=outcome.answer,
        citations=citation_items,
        route=RouteInfo(
            chosen=decision.chosen,
            confidence=decision.confidence,
            fallback_used=fallback_used,
        ),
        graph_paths=debug_graph_paths,
        passages=debug_passages,
        validation=ValidationResult(
            citation_resolution_passed=citation_passed,
            claim_support_status="not_evaluated",
            attempts=outcome.retries_used + 1,
        ),
        status=resp_status,
        latency_ms=LatencyBreakdown(
            route=t_route,
            retrieve=t_ret,
            generate=t_gen,
            total=t_total,
        ),
        request_id=request_id,
    )


@app.post("/query/baseline", response_model=QueryResponse)
def baseline_query_endpoint(
    req: QueryRequest,
    retrieval_engine: RetrievalEngine = Depends(get_engine),
) -> QueryResponse:
    """System A: Plain vector RAG baseline using identical generation conventions (PRD §8, §7.5)."""
    t0 = time.perf_counter()
    request_id = str(uuid.uuid4())

    # 1. Fixed route to vector baseline
    t_route = 0
    route_info = RouteInfo(chosen="vector", confidence=1.0, fallback_used=False)

    # 2. Vector retrieval only
    t_ret_0 = time.perf_counter()
    vector_passages = retrieval_engine.retrieve_vector(req.question, top_k=req.top_k)
    t_ret = int((time.perf_counter() - t_ret_0) * 1000)

    # 3. Context assembly (passages only, no graph facts)
    context_text, registry = assemble_context(
        graph_paths=[],
        vector_passages=vector_passages,
    )

    if not vector_passages:
        t_total = int((time.perf_counter() - t0) * 1000)
        log_routing_decision(
            question=req.question,
            route="vector_baseline",
            confidence=1.0,
            fallback_used=False,
            outcome="refused",
            latency_ms=t_total,
            request_id=request_id,
        )
        return QueryResponse(
            answer="No relevant evidence was found in the SEC filings to answer this question.",
            citations=[],
            route=route_info,
            graph_paths=[],
            passages=[],
            validation=ValidationResult(
                citation_resolution_passed=True,
                claim_support_status="not_evaluated",
                attempts=1,
            ),
            status="refused",
            latency_ms=LatencyBreakdown(route=0, retrieve=t_ret, generate=0, total=t_total),
            request_id=request_id,
        )

    # 4. Grounded Generation using matching prompt style & citation validator
    t_gen_0 = time.perf_counter()
    outcome = generate_grounded_answer(
        question=req.question,
        context_text=context_text,
        registry=registry,
        max_retries=2,
    )
    t_gen = int((time.perf_counter() - t_gen_0) * 1000)
    t_total = int((time.perf_counter() - t0) * 1000)

    citation_items = [
        CitationItem(
            label=c.label.strip("[]"),
            chunk_id=c.chunk_id,
            doc=c.doc_id or c.company or "SEC 10-K",
            section=c.section_path or "Filing",
            snippet=c.evidence_quote or (c.text_snippet[:200] if c.text_snippet else ""),
            supports_claim="unknown",
        )
        for c in outcome.citations
    ]

    resp_status: Any = "ok"
    if outcome.status == "refusal":
        resp_status = "refused"
    elif outcome.status == "needs_clarification":
        resp_status = "needs_clarification"
    elif outcome.status == "validation_failed":
        resp_status = "validation_failed"

    log_routing_decision(
        question=req.question,
        route="vector_baseline",
        confidence=1.0,
        fallback_used=False,
        outcome=resp_status,
        latency_ms=t_total,
        request_id=request_id,
    )

    debug_passages: list[dict[str, Any]] = []
    if req.debug:
        debug_passages = [vp.model_dump() for vp in vector_passages]

    citation_passed = outcome.resolution_rate >= 1.0 if outcome.citations else (outcome.status in ("refusal", "needs_clarification"))

    return QueryResponse(
        answer=outcome.answer,
        citations=citation_items,
        route=route_info,
        graph_paths=[],
        passages=debug_passages,
        validation=ValidationResult(
            citation_resolution_passed=citation_passed,
            claim_support_status="not_evaluated",
            attempts=outcome.retries_used + 1,
        ),
        status=resp_status,
        latency_ms=LatencyBreakdown(
            route=t_route,
            retrieve=t_ret,
            generate=t_gen,
            total=t_total,
        ),
        request_id=request_id,
    )


@app.get("/entities/{entity_id}", response_model=EntityDetailResponse)
def get_entity_detail(entity_id: str) -> EntityDetailResponse:
    """Retrieve canonical entity metadata, merge provenance, and connected graph relationships (PRD §8)."""
    # 1. Query PostgreSQL entities table
    ent_sql = "SELECT entity_id, canonical_name, type, aliases FROM entities WHERE entity_id = %(eid)s;"
    entity_row = None
    with pg_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ent_sql, {"eid": entity_id})
            entity_row = cur.fetchone()

    # If not found directly, check if it was absorbed into another canonical entity
    absorbed_into = None
    if not entity_row:
        with pg_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT canonical_entity_id FROM entity_merge_history WHERE source_entity_id = %(eid)s LIMIT 1;",
                    {"eid": entity_id},
                )
                merge_row = cur.fetchone()
                if merge_row:
                    absorbed_into = merge_row["canonical_entity_id"]
                    cur.execute(ent_sql, {"eid": absorbed_into})
                    entity_row = cur.fetchone()

    if not entity_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity with ID '{entity_id}' not found in canonical registry.",
        )

    target_eid = entity_row["entity_id"]

    # 2. Query Neo4j for node degree and top relationships
    degree = 0
    relationships: list[dict[str, Any]] = []
    try:
        with neo4j_db.get_session() as session:
            cypher = """
            MATCH (e:Entity {entity_id: $eid})
            OPTIONAL MATCH (e)-[r]->(t:Entity)
            RETURN e.canonical_name AS canonical_name,
                   COUNT { (e)--() } AS degree,
                   COLLECT(DISTINCT {relation: type(r), target_id: t.entity_id, target_name: t.canonical_name})[..25] AS relationships;
            """
            rec = session.run(cypher, eid=target_eid).single()
            if rec:
                degree = rec["degree"] or 0
                relationships = [rel for rel in rec["relationships"] if rel.get("relation")]
    except Exception as e:
        logger.warning("Could not query Neo4j for entity '%s': %s", target_eid, e)

    # 3. Query PostgreSQL entity_merge_history for entities merged into this one
    absorbed_entities: list[str] = []
    with pg_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source_entity_id FROM entity_merge_history WHERE canonical_entity_id = %(eid)s;",
                {"eid": target_eid},
            )
            absorbed_entities = [r["source_entity_id"] for r in cur.fetchall()]

    canonical_for = [absorbed_into] if absorbed_into else []

    return EntityDetailResponse(
        entity_id=target_eid,
        canonical_name=entity_row["canonical_name"],
        type=entity_row["type"],
        aliases=entity_row["aliases"] or [],
        degree=degree,
        relationships=relationships,
        absorbed_entities=absorbed_entities,
        canonical_for=canonical_for,
    )


@app.get("/chunks/{chunk_id}", response_model=ChunkDetailResponse)
def get_chunk_detail(chunk_id: str) -> ChunkDetailResponse:
    """Retrieve authoritative source chunk, SEC document metadata, and extraction observations (PRD §8)."""
    chunk_sql = """
    SELECT
        c.chunk_id,
        c.doc_id,
        c.section_path,
        c.item,
        c.text,
        c.token_count,
        c.entity_ids,
        d.company,
        d.ticker,
        d.cik,
        d.form_type,
        d.fiscal_year,
        d.filing_date,
        d.accession,
        d.source_url
    FROM chunks c
    JOIN documents d ON c.doc_id = d.doc_id
    WHERE c.chunk_id = %(chunk_id)s;
    """
    chunk_row = None
    with pg_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(chunk_sql, {"chunk_id": chunk_id})
            chunk_row = cur.fetchone()

    if not chunk_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk with ID '{chunk_id}' not found.",
        )

    # Query extraction observations attached to this chunk
    obs_sql = """
    SELECT observation_id, head_surface, relation_type, tail_surface, evidence_quote, evidence_verified
    FROM extraction_observations
    WHERE chunk_id = %(chunk_id)s
    LIMIT 50;
    """
    observations: list[ChunkObservationItem] = []
    with pg_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(obs_sql, {"chunk_id": chunk_id})
            for r in cur.fetchall():
                observations.append(
                    ChunkObservationItem(
                        observation_id=r["observation_id"],
                        head_surface=r["head_surface"],
                        relation_type=r["relation_type"],
                        tail_surface=r["tail_surface"],
                        evidence_quote=r["evidence_quote"],
                        evidence_verified=bool(r["evidence_verified"]),
                    )
                )

    return ChunkDetailResponse(
        chunk_id=chunk_row["chunk_id"],
        doc_id=chunk_row["doc_id"],
        company=chunk_row["company"],
        ticker=chunk_row["ticker"],
        cik=chunk_row["cik"],
        form_type=chunk_row["form_type"],
        fiscal_year=chunk_row["fiscal_year"],
        filing_date=str(chunk_row["filing_date"]),
        accession=chunk_row["accession"],
        section_path=chunk_row["section_path"],
        item=chunk_row["item"],
        text=chunk_row["text"],
        token_count=chunk_row["token_count"],
        entity_ids=chunk_row["entity_ids"] or [],
        source_url=chunk_row["source_url"],
        observations_count=len(observations),
        observations=observations,
    )
