"""PostgreSQL Ingestion Module for Documents, Chunks, and Parser Observations (PRD §9.1)."""

import logging

from psycopg.types.json import Jsonb

from kgrag.data.chunker import ChunkRecord
from kgrag.data.sec_fetcher import FilingMetadata
from kgrag.db.postgres import get_connection
from kgrag.extract.exhibit21 import ParserObservation

logger = logging.getLogger(__name__)


def ingest_document(metadata: FilingMetadata) -> None:
    """Store document metadata idempotently in PostgreSQL."""
    sql = """
    INSERT INTO documents (
        doc_id, company, ticker, cik, form_type, fiscal_year,
        filing_date, accession, source_url, sha256
    ) VALUES (
        %(doc_id)s, %(company)s, %(ticker)s, %(cik)s, %(form_type)s, %(fiscal_year)s,
        %(filing_date)s, %(accession)s, %(source_url)s, %(sha256)s
    )
    ON CONFLICT (doc_id) DO UPDATE SET
        company = EXCLUDED.company,
        fiscal_year = EXCLUDED.fiscal_year,
        filing_date = EXCLUDED.filing_date,
        source_url = EXCLUDED.source_url,
        sha256 = EXCLUDED.sha256;
    """
    params = {
        "doc_id": metadata.accession,
        "company": metadata.company,
        "ticker": metadata.ticker,
        "cik": metadata.cik,
        "form_type": metadata.form_type,
        "fiscal_year": metadata.fiscal_year,
        "filing_date": metadata.filing_date,
        "accession": metadata.accession,
        "source_url": metadata.source_url,
        "sha256": metadata.sha256,
    }
    with get_connection(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def ingest_chunks(chunks: list[ChunkRecord]) -> int:
    """Store section chunks idempotently in PostgreSQL."""
    if not chunks:
        return 0

    sql = """
    INSERT INTO chunks (
        chunk_id, doc_id, section_path, item, text,
        token_count, char_start, char_end, chunker_version
    ) VALUES (
        %(chunk_id)s, %(doc_id)s, %(section_path)s, %(item)s, %(text)s,
        %(token_count)s, %(char_start)s, %(char_end)s, %(chunker_version)s
    )
    ON CONFLICT (chunk_id) DO UPDATE SET
        text = EXCLUDED.text,
        token_count = EXCLUDED.token_count,
        char_start = EXCLUDED.char_start,
        char_end = EXCLUDED.char_end;
    """
    with get_connection(autocommit=False) as conn:
        with conn.cursor() as cur:
            for chunk in chunks:
                cur.execute(sql, chunk.model_dump())
        conn.commit()
    return len(chunks)


def ingest_parser_observations(observations: list[ParserObservation]) -> int:
    """Store parser observations idempotently in PostgreSQL."""
    if not observations:
        return 0

    sql = """
    INSERT INTO extraction_observations (
        observation_id, chunk_id, extraction_method, head_surface, head_type,
        relation_type, tail_surface, tail_type, evidence_quote, evidence_verified,
        model_confidence, role, year, validation_result
    ) VALUES (
        %(observation_id)s, %(chunk_id)s, %(extraction_method)s, %(head_surface)s, %(head_type)s,
        %(relation_type)s, %(tail_surface)s, %(tail_type)s, %(evidence_quote)s, %(evidence_verified)s,
        %(model_confidence)s, %(role)s, %(year)s, %(validation_result)s
    )
    ON CONFLICT (observation_id) DO UPDATE SET
        evidence_quote = EXCLUDED.evidence_quote,
        evidence_verified = EXCLUDED.evidence_verified,
        validation_result = EXCLUDED.validation_result;
    """
    with get_connection(autocommit=False) as conn:
        with conn.cursor() as cur:
            for obs in observations:
                data = obs.model_dump()
                data["validation_result"] = Jsonb(data["validation_result"])
                cur.execute(sql, data)
        conn.commit()
    return len(observations)
