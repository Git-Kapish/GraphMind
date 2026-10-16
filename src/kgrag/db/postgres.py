"""PostgreSQL connection and schema management with pgvector (PRD §9.1)."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from kgrag.config import get_settings

logger = logging.getLogger(__name__)


def get_connection(autocommit: bool = True) -> psycopg.Connection:
    """Get a direct psycopg connection to PostgreSQL with vector registration."""
    settings = get_settings().database.postgres
    conn = psycopg.connect(settings.dsn, autocommit=autocommit, row_factory=dict_row)
    try:
        register_vector(conn)
    except Exception as e:
        logger.warning("Could not register pgvector extension on connection: %s", e)
    return conn


@contextmanager
def get_db_cursor() -> Generator[psycopg.Cursor, None, None]:
    """Context manager yielding a database cursor with automatic cleanup."""
    conn = get_connection(autocommit=True)
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


def check_health() -> dict[str, Any]:
    """Verify PostgreSQL reachability and pgvector extension availability."""
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT 1 AS ok;")
            result = cur.fetchone()
            # Check vector extension
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            ext = cur.fetchone()
            vector_installed = ext is not None
            return {
                "status": "healthy" if result and result["ok"] == 1 else "unhealthy",
                "pgvector_installed": vector_installed,
            }
    except Exception as e:
        logger.error("PostgreSQL health check failed: %s", e)
        return {
            "status": "unreachable",
            "error": str(e),
            "pgvector_installed": False,
        }


def init_schema() -> bool:
    """Initialize database tables and indexes from schema.sql."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_path}")

    sql = schema_path.read_text(encoding="utf-8")
    with get_connection(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            logger.info("PostgreSQL schema successfully initialized.")
    return True
