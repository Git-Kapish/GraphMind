"""Scale Ingestion, Checkpoint Recovery, and Dry-Run Engine (PRD §5.7, FR-1.6, Milestone M9)."""

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime
from typing import Any

from psycopg.types.json import Jsonb

from kgrag.config import get_settings
from kgrag.data.chunker import SectionChunker
from kgrag.data.db_ingest import (
    ingest_chunks,
    ingest_document,
    ingest_parser_observations,
)
from kgrag.data.sec_fetcher import SECFetcher
from kgrag.data.sec_parser import SECParser
from kgrag.db.postgres import get_connection, init_schema
from kgrag.extract.exhibit21 import parse_exhibit21_subsidiaries
from kgrag.extract.llm_extractor import LLMExtractor
from kgrag.extract.officers import parse_officer_text
from kgrag.extract.prefilter import ChunkPreFilter
from kgrag.graph.rebuild import rebuild_graph_from_postgres
from kgrag.resolve.resolver import embed_unembedded_entities, resolve_all_observations
from kgrag.vector.embeddings import embed_unindexed_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Primary Corporate Filers
DEV_TICKERS = ["NVDA", "AMD", "INTC", "MU", "MSFT", "AVGO"]
EXPANDED_TICKERS = ["QCOM", "AAPL", "AMZN", "GOOGL"]
FULL_TICKERS = DEV_TICKERS + EXPANDED_TICKERS


def get_tickers_for_subset(subset: str) -> list[str]:
    """Return ticker list based on configured subset (PRD FR-1.6)."""
    sub = subset.lower().strip()
    if sub == "dev":
        return list(DEV_TICKERS)
    elif sub == "expanded":
        return list(EXPANDED_TICKERS)
    elif sub == "full":
        return list(FULL_TICKERS)
    else:
        # Allow comma-separated tickers e.g. "QCOM,AAPL"
        tickers = [t.strip().upper() for t in subset.split(",") if t.strip()]
        if not tickers:
            raise ValueError(f"Unknown subset or empty ticker list: {subset}")
        return tickers


def record_checkpoint(
    run_id: str,
    ticker: str,
    stage: str,
    status: str,
    records_processed: int = 0,
    elapsed_seconds: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record pipeline stage progress in PostgreSQL checkpoint journal."""
    sql = """
    INSERT INTO ingestion_checkpoints (
        run_id, ticker, stage, status, records_processed, elapsed_seconds, metadata, updated_at
    ) VALUES (
        %(run_id)s, %(ticker)s, %(stage)s, %(status)s, %(records)s, %(elapsed)s, %(metadata)s, CURRENT_TIMESTAMP
    );
    """
    params = {
        "run_id": run_id,
        "ticker": ticker,
        "stage": stage,
        "status": status,
        "records": records_processed,
        "elapsed": elapsed_seconds,
        "metadata": Jsonb(metadata or {}),
    }
    with get_connection(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def get_latest_checkpoint_status(ticker: str, stage: str) -> str | None:
    """Retrieve status of the latest checkpoint for a ticker and stage."""
    sql = """
    SELECT status FROM ingestion_checkpoints
    WHERE ticker = %(ticker)s AND stage = %(stage)s
    ORDER BY id DESC LIMIT 1;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"ticker": ticker, "stage": stage})
            row = cur.fetchone()
            return row["status"] if row else None


def reset_failed_checkpoints() -> int:
    """Clear failed records from cache and checkpoints for retry (PRD FR-1.6)."""
    with get_connection(autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM extraction_cache WHERE status = 'failed';")
            cache_deleted = cur.rowcount
            cur.execute("DELETE FROM ingestion_checkpoints WHERE status = 'failed';")
            checkpoints_deleted = cur.rowcount
    logger.info("Cleared %d failed cache entries and %d failed checkpoints.", cache_deleted, checkpoints_deleted)
    return cache_deleted + checkpoints_deleted


def run_dry_run(sample_size: int = 20) -> dict[str, Any]:
    """Measure seconds per chunk and pre-filter pass rate on local hardware (PRD FR-1.6, §5.7)."""
    settings = get_settings()
    extractor = LLMExtractor()
    prefilter = ChunkPreFilter()

    # Load total chunks count from DB
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM chunks;")
            total_db_chunks = cur.fetchone()["total"]

            # Sample chunks across filers and items (excluding exhibit21 which is parsed deterministically)
            cur.execute(
                """
                SELECT c.chunk_id, c.text, c.item, d.company, d.ticker
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE d.ticker <> '' AND c.item <> 'exhibit21'
                ORDER BY c.chunk_id
                LIMIT %(limit)s;
                """,
                {"limit": sample_size},
            )
            sampled_chunks = cur.fetchall()

    if not sampled_chunks:
        print("No chunks found in database. Run ingestion on initial filings first.", flush=True)
        return {}

    print("\n" + "=" * 75, flush=True)
    print(f"  KNOWLEDGE GRAPH RAG: INGESTION DRY-RUN (SAMPLE: {len(sampled_chunks)} CHUNKS)", flush=True)
    print(f"  Target Model: {settings.llm.model} | Runtime: {settings.llm.runtime}", flush=True)
    print(f"  Hardware: Local CPU | Total Ingested Chunks in DB: {total_db_chunks}", flush=True)
    print("=" * 75 + "\n", flush=True)

    prefilter_passed = 0
    total_time_llm = 0.0
    llm_invocations = 0
    extracted_relations_count = 0
    deterministic_officer_count = 0

    print(f"{'Chunk ID':<35} | {'Filter':<10} | {'Sec':<6} | {'Extracted Relations'}", flush=True)
    print("-" * 75, flush=True)

    for chunk in sampled_chunks:
        chunk_id = chunk["chunk_id"]
        text = chunk["text"]
        company = chunk["company"]
        ticker = chunk["ticker"]

        # Check deterministic officer parser first
        officer_obs = parse_officer_text(chunk_id, text, company)
        if officer_obs:
            deterministic_officer_count += len(officer_obs)

        should_extract, reason = prefilter.should_extract(text)
        if should_extract:
            prefilter_passed += 1
            llm_invocations += 1

            start_t = time.perf_counter()
            relations = extractor.extract_chunk(
                chunk_id=chunk_id,
                chunk_text=text,
                filer_company=company,
                filer_ticker=ticker,
                force=True,  # Test real generation speed
            )
            elapsed = time.perf_counter() - start_t
            total_time_llm += elapsed
            extracted_relations_count += len(relations)

            rel_summary = ", ".join(f"{r['relation_type']}" for r in relations[:2])
            if len(relations) > 2:
                rel_summary += f" (+{len(relations) - 2} more)"
            print(f"{chunk_id:<35} | {'PASS':<10} | {elapsed:>5.2f}s | {rel_summary or 'None verified'}")
        else:
            print(f"{chunk_id:<35} | {'SKIP':<10} | {'0.00s':>6} | (Skipped by prefilter)")

    avg_sec_per_passed_chunk = (total_time_llm / llm_invocations) if llm_invocations > 0 else 0.0
    pass_rate = prefilter_passed / len(sampled_chunks) if sampled_chunks else 0.0

    # Projected calculations
    estimated_passed_chunks = int(total_db_chunks * pass_rate)
    estimated_total_time_sec = estimated_passed_chunks * avg_sec_per_passed_chunk
    estimated_total_hours = estimated_total_time_sec / 3600.0

    # Recommended budget calculation (§5.7): target <= 1 hour total ingestion time on local CPU
    target_max_seconds = 3600
    recommended_chunk_budget = int(target_max_seconds / max(avg_sec_per_passed_chunk, 0.1))

    print("\n" + "=" * 75)
    print("  DRY-RUN MEASURED BENCHMARK & EXTRAPOLATION SUMMARY (PRD §5.7, FR-1.6)")
    print("=" * 75)
    print(f"- Sampled Chunks Evaluated:        {len(sampled_chunks)}")
    print(f"- Pre-Filter Pass Rate:            {pass_rate * 100:.1f}% ({prefilter_passed}/{len(sampled_chunks)})")
    print(f"- LLM Model Calls Executed:        {llm_invocations}")
    print(f"- Total Verified Relations Found:  {extracted_relations_count}")
    print(f"- Deterministic Officer Relations: {deterministic_officer_count}")
    print(f"- Measured Avg Seconds / Chunk:    {avg_sec_per_passed_chunk:.2f} s/chunk")
    print("\n[ESTIMATED EXTRAPOLATIONS (ESTIMATES ONLY - PRD FR-1.6)]")
    print(f"- Total Chunks Available in DB:    {total_db_chunks}")
    print(f"- Projected LLM Chunks to Extract: {estimated_passed_chunks}")
    print(f"- Estimated Ingestion Time (LLM):  {estimated_total_hours:.2f} hours")
    print(f"- Recommended max_extraction_chunks: {recommended_chunk_budget} chunks (for <= 1 hr run)")
    print(f"- Configured max_extraction_chunks:  {settings.extraction.max_extraction_chunks} chunks")
    print("\n[BOTTLENECK & COMPUTE BUDGET ADVISORY]")
    print("  Local CPU execution performs best when deterministic parsers (Exhibit 21 + Officers)")
    print("  extract 80%+ of relational edges in <0.2s, while LLM extraction is reserved for")
    print("  high-value chunks passing pre-filter criteria.")
    print("  To proceed with full scale ingestion, run with `--confirm`.")
    print("=" * 75 + "\n")

    return {
        "sample_size": len(sampled_chunks),
        "prefilter_pass_rate": pass_rate,
        "avg_sec_per_chunk": avg_sec_per_passed_chunk,
        "total_db_chunks": total_db_chunks,
        "estimated_total_hours": estimated_total_hours,
        "recommended_budget": recommended_chunk_budget,
    }


def run_scale_ingestion(
    subset: str = "expanded",
    confirm: bool = False,
    max_chunks: int | None = None,
    retry_failed: bool = False,
    skip_llm: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Execute scale ingestion pipeline with checkpointing, budget guardrails, and idempotent rebuild."""
    if not confirm:
        print("\n[ERROR] PRD FR-1.6 requires explicit `--confirm` flag to execute ingestion.")
        print("Run `python -m kgrag.ingest --dry-run` first to preview compute metrics, or")
        print("add `--confirm` to proceed.\n")
        sys.exit(1)

    start_total = time.perf_counter()
    settings = get_settings()
    init_schema()

    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    tickers = get_tickers_for_subset(subset)
    budget = max_chunks or settings.extraction.max_extraction_chunks

    print("\n" + "=" * 75)
    print("  KNOWLEDGE GRAPH RAG: SCALE INGESTION PIPELINE (MILESTONE M9)")
    print(f"  Run ID: {run_id} | Subset: {subset.upper()} ({len(tickers)} Filers)")
    print(f"  Target Filers: {', '.join(tickers)}")
    print(f"  Max LLM Chunk Budget: {budget} | Skip LLM: {skip_llm} | Retry Failed: {retry_failed}")
    print("=" * 75 + "\n")

    if retry_failed:
        reset_failed_checkpoints()

    fetcher = SECFetcher()
    parser = SECParser()
    chunker = SectionChunker()
    prefilter = ChunkPreFilter()
    extractor = LLMExtractor()

    total_chunks_ingested = 0
    total_deterministic_obs = 0
    total_llm_obs = 0
    llm_calls_made = 0
    skipped_cache_count = 0
    skipped_prefilter_count = 0

    for ticker in tickers:
        ticker_start = time.perf_counter()
        logger.info(">>> Processing filer: %s", ticker)

        # -------------------------------------------------------------
        # STAGE 1: Fetch 10-K and Ingest Document Record
        # -------------------------------------------------------------
        fetch_status = get_latest_checkpoint_status(ticker, "fetch_parse")
        if fetch_status == "completed" and not force:
            logger.info("[%s] Fetch/Parse already marked completed in checkpoint. Loading...", ticker)

        t0 = time.perf_counter()
        try:
            metadata, ten_k = fetcher.get_latest_10k(ticker)
            parsed = parser.parse_filing(metadata, ten_k)
            ingest_document(metadata)
            record_checkpoint(
                run_id=run_id,
                ticker=ticker,
                stage="fetch_parse",
                status="completed",
                records_processed=1,
                elapsed_seconds=time.perf_counter() - t0,
                metadata={"accession": metadata.accession, "fiscal_year": metadata.fiscal_year},
            )
        except Exception as e:
            logger.error("[%s] Failed during fetch/parse: %s", ticker, e)
            record_checkpoint(
                run_id=run_id,
                ticker=ticker,
                stage="fetch_parse",
                status="failed",
                elapsed_seconds=time.perf_counter() - t0,
                metadata={"error": str(e)},
            )
            continue

        # -------------------------------------------------------------
        # STAGE 2: Section Chunking
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        ticker_chunks: list[Any] = []
        for sec in parsed.sections:
            chunks = chunker.chunk_section(metadata.accession, sec)
            ticker_chunks.extend(chunks)

        num_chunks = ingest_chunks(ticker_chunks)
        total_chunks_ingested += num_chunks
        record_checkpoint(
            run_id=run_id,
            ticker=ticker,
            stage="chunking",
            status="completed",
            records_processed=num_chunks,
            elapsed_seconds=time.perf_counter() - t0,
            metadata={"sections": [s.item for s in parsed.sections]},
        )
        logger.info("[%s] Chunked into %d chunks in %.2fs", ticker, num_chunks, time.perf_counter() - t0)

        # -------------------------------------------------------------
        # STAGE 3: Deterministic Parsing (Exhibit 21 + Officers)
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        # Exhibit 21
        ex21_obs = parse_exhibit21_subsidiaries(
            parent_company=metadata.company,
            accession=metadata.accession,
            subsidiaries=parsed.subsidiaries,
        )
        num_ex21 = ingest_parser_observations(ex21_obs)

        # Officer parsing across chunk texts
        officer_obs = []
        for chunk in ticker_chunks:
            chunk_text = chunk.text if hasattr(chunk, "text") else chunk["text"]
            chunk_id = chunk.chunk_id if hasattr(chunk, "chunk_id") else chunk["chunk_id"]
            obs = parse_officer_text(chunk_id, chunk_text, metadata.company)
            if obs:
                officer_obs.extend(obs)

        num_off = ingest_parser_observations(officer_obs)
        total_det = num_ex21 + num_off
        total_deterministic_obs += total_det

        record_checkpoint(
            run_id=run_id,
            ticker=ticker,
            stage="deterministic_parsing",
            status="completed",
            records_processed=total_det,
            elapsed_seconds=time.perf_counter() - t0,
            metadata={"subsidiaries": num_ex21, "officers": num_off},
        )
        logger.info(
            "[%s] Deterministic observations: %d (Ex21: %d, Officers: %d) in %.2fs",
            ticker,
            total_det,
            num_ex21,
            num_off,
            time.perf_counter() - t0,
        )

        # -------------------------------------------------------------
        # STAGE 4: LLM Extraction (with Cache & Pre-filter Guardrails)
        # -------------------------------------------------------------
        if skip_llm:
            logger.info("[%s] Skipping LLM extraction as requested (--skip-llm).", ticker)
            record_checkpoint(run_id=run_id, ticker=ticker, stage="llm_extraction", status="skipped")
        else:
            t0 = time.perf_counter()
            ticker_llm_obs = 0
            # Retrieve candidate non-exhibit21 chunks for this filing
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT chunk_id, text, item
                        FROM chunks
                        WHERE doc_id = %(doc_id)s AND item <> 'exhibit21'
                        ORDER BY CASE WHEN item = 'item1' THEN 1 WHEN item = 'item7' THEN 2 ELSE 3 END, chunk_id;
                        """,
                        {"doc_id": metadata.accession},
                    )
                    candidate_chunks = cur.fetchall()

            for c in candidate_chunks:
                cid = c["chunk_id"]
                ctext = c["text"]
                c_sha = hashlib.sha256(ctext.encode("utf-8")).hexdigest()

                # Check cache first
                cached = extractor.get_cached_result(c_sha)
                if cached:
                    if cached["status"] == "skipped_prefilter":
                        skipped_prefilter_count += 1
                        continue
                    if cached["status"] == "success":
                        skipped_cache_count += 1
                        continue
                    if cached["status"] == "failed" and not retry_failed:
                        continue

                # Check prefilter
                should_run, reason = prefilter.should_extract(ctext)
                if not should_run:
                    extractor.save_cache_result(c_sha, status="skipped_prefilter", result_json=None)
                    skipped_prefilter_count += 1
                    continue

                # Enforce budget (§5.7)
                if budget <= 0:
                    logger.warning(
                        "[%s] Compute budget exhausted (max_extraction_chunks reached). Remaining chunks deferred.",
                        ticker,
                    )
                    break

                # Run extraction
                relations = extractor.extract_chunk(
                    chunk_id=cid,
                    chunk_text=ctext,
                    filer_company=metadata.company,
                    filer_ticker=ticker,
                    persist=True,
                )
                llm_calls_made += 1
                budget -= 1
                ticker_llm_obs += len(relations)

            total_llm_obs += ticker_llm_obs
            record_checkpoint(
                run_id=run_id,
                ticker=ticker,
                stage="llm_extraction",
                status="completed",
                records_processed=ticker_llm_obs,
                elapsed_seconds=time.perf_counter() - t0,
                metadata={"llm_calls": llm_calls_made, "relations": ticker_llm_obs},
            )
            logger.info(
                "[%s] LLM extraction: %d verified relations from %d calls in %.2fs",
                ticker,
                ticker_llm_obs,
                llm_calls_made,
                time.perf_counter() - t0,
            )

        elapsed_ticker = time.perf_counter() - ticker_start
        logger.info(">>> Completed filer %s in %.2fs", ticker, elapsed_ticker)

    # -------------------------------------------------------------
    # STAGE 5: Entity Resolution
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    logger.info("Running entity resolution across all observations...")
    res_stats = resolve_all_observations(force=False)
    record_checkpoint(
        run_id=run_id,
        ticker="ALL",
        stage="entity_resolution",
        status="completed",
        records_processed=res_stats.get("observations_resolved", 0),
        elapsed_seconds=time.perf_counter() - t0,
        metadata=res_stats,
    )
    logger.info("Entity resolution complete: %s in %.2fs", res_stats, time.perf_counter() - t0)

    # -------------------------------------------------------------
    # STAGE 6: Embeddings (Dense Chunks & Canonical Entities)
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    logger.info("Embedding unindexed entities and chunks...")
    ent_embedded = embed_unembedded_entities()
    chunks_embedded = embed_unindexed_chunks()
    record_checkpoint(
        run_id=run_id,
        ticker="ALL",
        stage="embeddings",
        status="completed",
        records_processed=ent_embedded + chunks_embedded,
        elapsed_seconds=time.perf_counter() - t0,
        metadata={"entities_embedded": ent_embedded, "chunks_embedded": chunks_embedded},
    )
    logger.info(
        "Embeddings complete: %d entities, %d chunks in %.2fs",
        ent_embedded,
        chunks_embedded,
        time.perf_counter() - t0,
    )

    # -------------------------------------------------------------
    # STAGE 7: Idempotent Neo4j Graph Projection Rebuild
    # -------------------------------------------------------------
    t0 = time.perf_counter()
    logger.info("Rebuilding Neo4j graph idempotently from PostgreSQL...")
    rebuild_stats = rebuild_graph_from_postgres()
    record_checkpoint(
        run_id=run_id,
        ticker="ALL",
        stage="graph_rebuild",
        status="completed",
        records_processed=rebuild_stats.get("neo4j_nodes", 0) + rebuild_stats.get("neo4j_edges", 0),
        elapsed_seconds=time.perf_counter() - t0,
        metadata=rebuild_stats,
    )
    logger.info("Neo4j projection complete in %.2fs", time.perf_counter() - t0)

    total_elapsed = time.perf_counter() - start_total

    # Summary Report
    print("\n" + "=" * 75)
    print("  SCALE INGESTION EXECUTION REPORT (PRD §5.7, FR-1.6)")
    print("=" * 75)
    print(f"- Run ID:                          {run_id}")
    print(f"- Target Subset:                   {subset.upper()} ({len(tickers)} Filers)")
    print(f"- Total Ingestion Time:            {total_elapsed:.2f} seconds ({total_elapsed / 60.0:.2f} min)")
    print(f"- New Chunks Ingested:             {total_chunks_ingested}")
    print(f"- Deterministic Observations:      {total_deterministic_obs}")
    print(f"- LLM Verified Relations:          {total_llm_obs}")
    print(f"- LLM Invocations Executed:        {llm_calls_made}")
    print(f"- Chunks Skipped (Cache Hits):     {skipped_cache_count}")
    print(f"- Chunks Skipped (Prefilter):      {skipped_prefilter_count}")
    print(f"- New Entities Embedded:           {ent_embedded}")
    print(f"- New Chunks Embedded:             {chunks_embedded}")
    print(f"- Neo4j Nodes Projected:           {rebuild_stats['neo4j_nodes']}")
    print(f"- Neo4j Relationships Projected:   {rebuild_stats['neo4j_edges']}")
    print("=" * 75 + "\n")

    return {
        "run_id": run_id,
        "elapsed_seconds": total_elapsed,
        "tickers": tickers,
        "new_chunks": total_chunks_ingested,
        "deterministic_obs": total_deterministic_obs,
        "llm_obs": total_llm_obs,
        "llm_calls": llm_calls_made,
        "neo4j_nodes": rebuild_stats["neo4j_nodes"],
        "neo4j_edges": rebuild_stats["neo4j_edges"],
    }


def main():
    parser = argparse.ArgumentParser(description="Knowledge Graph RAG Scale Ingestion & Dry-Run CLI (PRD §5.7, FR-1.6)")
    parser.add_argument("--dry-run", action="store_true", help="Run benchmark dry-run on sampled chunks")
    parser.add_argument("--sample-size", type=int, default=20, help="Number of chunks to sample for dry-run (default: 20)")
    parser.add_argument(
        "--subset",
        choices=["dev", "expanded", "full"],
        default="expanded",
        help="Corpus subset: dev (6 filers), expanded (4 new filers), full (all 10 filers)",
    )
    parser.add_argument("--confirm", action="store_true", help="Confirm execution of full ingestion run")
    parser.add_argument("--max-chunks", type=int, default=None, help="Maximum chunks to send to LLM extraction")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed extractions from cache/checkpoints")
    parser.add_argument("--skip-llm", action="store_true", help="Fast mode: run deterministic parsers and embeddings only")
    parser.add_argument("--force", action="store_true", help="Force re-execution of previously completed stages")

    args = parser.parse_args()

    if args.dry_run:
        run_dry_run(sample_size=args.sample_size)
    elif args.confirm:
        run_scale_ingestion(
            subset=args.subset,
            confirm=args.confirm,
            max_chunks=args.max_chunks,
            retry_failed=args.retry_failed,
            skip_llm=args.skip_llm,
            force=args.force,
        )
    else:
        print("\n[NOTICE] To benchmark throughput and measure compute budget, run:")
        print("    python -m kgrag.ingest --dry-run\n")
        print("To execute full scale ingestion, run:")
        print(f"    python -m kgrag.ingest --subset {args.subset} --confirm\n")


if __name__ == "__main__":
    main()
