"""Dense embedding pipeline and pgvector baseline retrieval (PRD §7, §11)."""

import logging
import time
from typing import Any

from kgrag.config import get_settings
from kgrag.db.postgres import get_connection
from kgrag.llm.client import get_llm_client

logger = logging.getLogger(__name__)


def embed_unindexed_chunks(batch_size: int = 16) -> int:
    """Generate vector embeddings for any chunks in PostgreSQL lacking embeddings."""
    llm = get_llm_client()
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

        embeddings = llm.embed(texts)
        if len(embeddings) != len(batch):
            logger.warning("Embeddings count mismatch (%d != %d)", len(embeddings), len(batch))
            continue

        with get_connection(autocommit=True) as conn:
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
        updated += len(batch)
        if (i // batch_size) % 5 == 0 or updated == total_chunks:
            logger.info("Embedded [%d/%d] chunks...", updated, total_chunks)

    elapsed = time.perf_counter() - start_t
    logger.info("Finished embedding %d chunks in %.2f seconds.", updated, elapsed)
    return updated


def query_vector_baseline(query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Query PostgreSQL using pgvector cosine distance (System A: Vector Baseline)."""
    llm = get_llm_client()
    query_embs = llm.embed([query_text])
    if not query_embs:
        return []
    query_vec = query_embs[0]

    sql = """
    SELECT
        c.chunk_id,
        c.text,
        c.item,
        d.company,
        d.ticker,
        1 - (c.embedding <=> %(query_vec)s::vector) AS cosine_similarity
    FROM chunks c
    JOIN documents d ON c.doc_id = d.doc_id
    WHERE c.embedding IS NOT NULL
    ORDER BY c.embedding <=> %(query_vec)s::vector
    LIMIT %(top_k)s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"query_vec": str(query_vec), "top_k": top_k})
            return cur.fetchall()


if __name__ == "__main__":
    embed_unindexed_chunks()
