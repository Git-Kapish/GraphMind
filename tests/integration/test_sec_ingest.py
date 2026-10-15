"""Integration tests verifying PostgreSQL ingestion of filings, chunks, and Exhibit 21 observations."""

from kgrag.db.postgres import get_connection


def test_database_has_ingested_dev_filings():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Verify documents table
            cur.execute(
                "SELECT ticker, accession FROM documents WHERE ticker IN ('NVDA', 'AMD', 'INTC', 'MU', 'MSFT', 'AVGO');"
            )
            docs = cur.fetchall()
            assert len(docs) >= 5, f"Expected at least 5 dev filers in documents, found {len(docs)}"

            # Verify chunks table
            cur.execute("SELECT COUNT(*) AS total_chunks FROM chunks;")
            res_chunks = cur.fetchone()
            assert res_chunks["total_chunks"] >= 300, (
                f"Expected >= 300 chunks, found {res_chunks['total_chunks']}"
            )

            # Verify extraction_observations has Exhibit 21 entries
            cur.execute(
                "SELECT COUNT(*) AS total_obs FROM extraction_observations WHERE extraction_method = 'parser';"
            )
            res_obs = cur.fetchone()
            assert res_obs["total_obs"] >= 100, (
                f"Expected >= 100 parser observations, found {res_obs['total_obs']}"
            )
