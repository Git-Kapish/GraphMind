"""Neo4j driver and schema management (PRD §9.2)."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from neo4j import Driver, GraphDatabase, Session

from kgrag.config import get_settings

logger = logging.getLogger(__name__)

_driver: Driver | None = None


def get_driver() -> Driver:
    """Get or create singleton Neo4j driver."""
    global _driver
    if _driver is None:
        settings = get_settings().database.neo4j
        _driver = GraphDatabase.driver(
            settings.uri,
            auth=(settings.user, settings.password),
            max_connection_lifetime=30 * 60,
            max_connection_pool_size=50,
            connection_acquisition_timeout=10.0,
        )
    return _driver


def close_driver() -> None:
    """Close Neo4j driver connection."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


@contextmanager
def get_session(database: str = "neo4j") -> Generator[Session, None, None]:
    """Context manager yielding a Neo4j session."""
    driver = get_driver()
    session = driver.session(database=database)
    try:
        yield session
    finally:
        session.close()


def check_health() -> dict[str, Any]:
    """Verify Neo4j connectivity and server information."""
    try:
        driver = get_driver()
        with driver.session() as session:
            result = session.run("RETURN 1 AS ok").single()
            if result and result["ok"] == 1:
                return {
                    "status": "healthy",
                    "edition": "community",
                }
            return {"status": "unhealthy"}
    except Exception as e:
        logger.error("Neo4j health check failed: %s", e)
        return {
            "status": "unreachable",
            "error": str(e),
        }


def init_constraints() -> bool:
    """Initialize unique constraints and indexes for Entity nodes (PRD §9.2)."""
    driver = get_driver()
    with driver.session() as session:
        # Constraint for unique entity_id
        session.run(
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS "
            "FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE"
        )
        # Index on canonical_name
        session.run(
            "CREATE INDEX entity_canonical_name IF NOT EXISTS FOR (e:Entity) ON (e.canonical_name)"
        )
        logger.info("Neo4j constraints and indexes initialized successfully.")
    return True
