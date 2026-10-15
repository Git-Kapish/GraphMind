"""FastAPI application for Knowledge Graph RAG (PRD §8)."""

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kgrag import __version__
from kgrag.api.models import ComponentHealth, HealthResponse
from kgrag.db import neo4j as neo4j_db
from kgrag.db import postgres as pg_db
from kgrag.llm.client import get_llm_client

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

    # Determine overall status
    all_healthy = all(c.status == "healthy" for c in components.values())
    any_healthy = any(c.status == "healthy" for c in components.values())
    overall_status = "ok" if all_healthy else ("degraded" if any_healthy else "unhealthy")

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(UTC).isoformat(),
        version=__version__,
        components=components,
    )
