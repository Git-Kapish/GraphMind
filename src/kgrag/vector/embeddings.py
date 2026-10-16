"""Dense embedding pipeline and pgvector baseline retrieval (PRD §7, §11)."""

import logging
import time
from typing import Any

from kgrag.config import get_settings
from kgrag.db.postgres import get_connection
from kgrag.llm.client import get_llm_client

logger = logging.getLogger(__name__)


def embed_unindexed_chunks(batch_size: int = 16, llm: Any | None = None) -> int:
    """Generate vector embeddings for any chunks in PostgreSQL lacking embeddings."""
    embedder = llm or get_llm_client()
    settings = get_settings()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chunk_id, text
                FROM chunks
                WHERE embedding IS NULL
                ORDER BY chunk_id;
                """
            )
            rows = cur.fetchall()

    if not rows:
        logger.info("All chunks already have embeddings.")
        return 0

    total_chunks = len(rows)
    logger.info("Generating embeddings for %d chunks in batches of %d...", total_chunks, batch_size)
    start_t = time.perf_counter()

    updated = 0
    update_sql = """
    UPDATE chunks
    SET embedding = %(embedding)s::vector,
        embedding_model = %(model)s
    WHERE chunk_id = %(chunk_id)s;
    """

    for i in range(0, total_chunks, batch_size):
        batch = rows[i : i + batch_size]
        texts = [r["text"][:2000] for r in batch]  # Cap input text for embedder

        embeddings = embedder.embed(texts)
        if len(embeddings) != len(batch):
            logger.warning("Embeddings count mismatch (%d != %d)", len(embeddings), len(batch))
            continue

        with get_connection(autocommit=False) as conn:
            with conn.cursor() as cur:
                for r, emb in zip(batch, embeddings):
                    cur.execute(
                        update_sql,
                        {
                            "chunk_id": r["chunk_id"],
                            "embedding": str(emb),
                            "model": settings.embedding.model,
                        },
                    )
            conn.commit()
        updated += len(batch)
        if (i // batch_size) % 5 == 0 or updated == total_chunks:
            logger.info("Embedded [%d/%d] chunks...", updated, total_chunks)

    elapsed = time.perf_counter() - start_t
    logger.info("Finished embedding %d chunks in %.2f seconds.", updated, elapsed)
    return updated


def validate_vector_dimensions() -> dict[str, Any]:
    """Validate that PostgreSQL pgvector column dimensions strictly agree with configured settings (PRD FR-2.5)."""
    settings = get_settings()
    expected_dim = settings.embedding.dimension

    sql = """
    SELECT attrelid::regclass::text AS table_name, attname, atttypmod
    FROM pg_attribute
    WHERE attrelid IN ('chunks'::regclass, 'entities'::regclass)
      AND attname IN ('embedding', 'name_embedding');
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    for r in rows:
        actual_dim = r["atttypmod"]
        if actual_dim != expected_dim:
            raise ValueError(
                f"Vector dimension mismatch on {r['table_name']}.{r['attname']}: "
                f"PostgreSQL column is vector({actual_dim}) but config/settings.yaml specifies {expected_dim}. "
                "Changing dimension requires an explicit schema migration."
            )

    logger.info(
        "Vector dimensions validated: all tables aligned with %d-d embeddings.", expected_dim
    )
    return {"status": "ok", "dimension": expected_dim, "checked": len(rows)}


def migrate_vector_dimensions(
    target_dim: int = 2048, reset_existing: bool = True
) -> dict[str, Any]:
    """Migrate PostgreSQL pgvector column dimensions and reset legacy vectors to prevent mixing (PRD FR-2.5).

    Args:
        target_dim: The new embedding vector dimension (default 2048 for nvidia/nemotron-3-embed-1b:free).
        reset_existing: If True, sets legacy embeddings to NULL to prevent mixed vector space contamination.

    Returns:
        Summary dictionary with previous dimensions, new dimension, and unindexed chunk count.
    """
    dim_sql = """
    SELECT attrelid::regclass::text AS table_name, attname, atttypmod
    FROM pg_attribute
    WHERE attrelid IN ('chunks'::regclass, 'entities'::regclass)
      AND attname IN ('embedding', 'name_embedding');
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(dim_sql)
            rows = cur.fetchall()

    prev_dims = {f"{r['table_name']}.{r['attname']}": r["atttypmod"] for r in rows}
    needs_migration = any(dim != target_dim for dim in prev_dims.values())

    if not needs_migration:
        logger.info("All vector columns already aligned with %d-d.", target_dim)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) as unindexed FROM chunks WHERE embedding IS NULL;")
                unindexed = cur.fetchone()["unindexed"]
        return {
            "status": "already_aligned",
            "dimension": target_dim,
            "dimensions": prev_dims,
            "unindexed_chunks": unindexed,
        }

    logger.warning("Migrating vector columns from %s to %d-d...", prev_dims, target_dim)

    migration_commands = [
        "DROP INDEX IF EXISTS idx_chunks_embedding;",
        "DROP INDEX IF EXISTS idx_entities_name_embedding;",
        f"ALTER TABLE chunks ALTER COLUMN embedding TYPE vector({target_dim}) USING NULL;",
        f"ALTER TABLE entities ALTER COLUMN name_embedding TYPE vector({target_dim}) USING NULL;",
    ]
    if reset_existing:
        migration_commands.extend(
            [
                "UPDATE chunks SET embedding = NULL, embedding_model = NULL;",
                "UPDATE entities SET name_embedding = NULL, embedding_model = NULL;",
            ]
        )

    if target_dim <= 2000:
        migration_commands.extend(
            [
                "CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);",
                "CREATE INDEX IF NOT EXISTS idx_entities_name_embedding ON entities USING hnsw (name_embedding vector_cosine_ops);",
            ]
        )
    else:
        migration_commands.extend(
            [
                f"CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING hnsw ((embedding::halfvec({target_dim})) halfvec_cosine_ops);",
                f"CREATE INDEX IF NOT EXISTS idx_entities_name_embedding ON entities USING hnsw ((name_embedding::halfvec({target_dim})) halfvec_cosine_ops);",
            ]
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            for cmd in migration_commands:
                try:
                    cur.execute(cmd)
                except Exception as e:
                    logger.warning("Migration command error: %s (%s)", cmd, e)

            cur.execute("SELECT count(*) as unindexed FROM chunks WHERE embedding IS NULL;")
            unindexed = cur.fetchone()["unindexed"]

    logger.info(
        "Successfully migrated vector columns to %d-d. %d chunks ready for re-embedding.",
        target_dim,
        unindexed,
    )
    return {
        "status": "migrated",
        "previous_dimensions": prev_dims,
        "new_dimension": target_dim,
        "unindexed_chunks": unindexed,
    }


def query_vector_baseline(
    query_text: str,
    top_k: int = 5,
    item_filter: str | None = None,
    ticker_filter: str | None = None,
    llm: Any | None = None,
) -> list[dict[str, Any]]:
    """Query PostgreSQL using pgvector cosine distance (System A: Vector Baseline, PRD §7.2, §11)."""
    embedder = llm or get_llm_client()
    query_embs = embedder.embed([query_text])
    if not query_embs:
        return []
    query_vec = query_embs[0]

    conditions = ["c.embedding IS NOT NULL"]
    params: dict[str, Any] = {"query_vec": str(query_vec), "top_k": top_k}

    if item_filter:
        conditions.append("c.item = %(item_filter)s")
        params["item_filter"] = item_filter
    if ticker_filter:
        conditions.append("d.ticker = %(ticker_filter)s")
        params["ticker_filter"] = ticker_filter.upper()

    where_clause = " AND ".join(conditions)

    sql = f"""
    SELECT
        c.chunk_id,
        c.doc_id,
        c.section_path,
        c.item,
        c.text,
        c.entity_ids,
        d.company,
        d.ticker,
        d.filing_date,
        1 - (c.embedding <=> %(query_vec)s::vector) AS cosine_similarity
    FROM chunks c
    JOIN documents d ON c.doc_id = d.doc_id
    WHERE {where_clause}
    ORDER BY c.embedding <=> %(query_vec)s::vector
    LIMIT %(top_k)s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


if __name__ == "__main__":
    validate_vector_dimensions()
    embed_unindexed_chunks()
