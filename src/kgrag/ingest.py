"""Ingestion and Dry-Run CLI with compute budget measurement (PRD FR-1.6, §5.7)."""

import argparse
import logging
import sys
import time
from typing import Any

from kgrag.config import get_settings
from kgrag.db.postgres import get_connection
from kgrag.extract.llm_extractor import LLMExtractor
from kgrag.extract.officers import parse_officer_text
from kgrag.extract.prefilter import ChunkPreFilter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def run_dry_run(sample_size: int = 20) -> dict[str, Any]:
    """Measure seconds per chunk and pre-filter pass rate on local hardware (PRD FR-1.6)."""
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
        print("No chunks found in database. Run feasibility pipeline first.", flush=True)
        return {}

    print("\n" + "=" * 70, flush=True)
    print(f"  KNOWLEDGE GRAPH RAG: INGESTION DRY-RUN (SAMPLE: {len(sampled_chunks)} CHUNKS)", flush=True)
    print(f"  Target Model: {settings.llm.model} | Runtime: {settings.llm.runtime}", flush=True)
    print(f"  Hardware: Local CPU | Total Ingested Chunks Available: {total_db_chunks}", flush=True)
    print("=" * 70 + "\n", flush=True)

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

    # Recommended budget calculation (§5.7)
    # Target < 1 hour total ingestion time on local CPU
    target_max_seconds = 3600
    recommended_chunk_budget = int(target_max_seconds / max(avg_sec_per_passed_chunk, 0.1))

    print("\n" + "=" * 70)
    print("  DRY-RUN MEASURED BENCHMARK & EXTRAPOLATION SUMMARY")
    print("=" * 70)
    print(f"- Sampled Chunks Evaluated:        {len(sampled_chunks)}")
    print(f"- Pre-Filter Pass Rate:            {pass_rate * 100:.1f}% ({prefilter_passed}/{len(sampled_chunks)})")
    print(f"- LLM Model Calls Executed:        {llm_invocations}")
    print(f"- Total Verified Relations Found:  {extracted_relations_count}")
    print(f"- Deterministic Officer Relations: {deterministic_officer_count}")
    print(f"- Measured Avg Seconds / Chunk:    {avg_sec_per_passed_chunk:.2f} s/chunk")
    print("\n[ESTIMATED EXTRAPOLATIONS (ESTIMATES ONLY - PRD FR-1.6)]")
    print(f"- Total Chunks in Dev Corpus:      {total_db_chunks}")
    print(f"- Projected LLM Chunks to Extract: {estimated_passed_chunks}")
    print(f"- Recommended max_extraction_chunks: {recommended_chunk_budget} chunks (for <= 1 hr run)")
    print("=" * 70 + "\n")

    return {
        "sample_size": len(sampled_chunks),
        "prefilter_pass_rate": pass_rate,
        "avg_sec_per_chunk": avg_sec_per_passed_chunk,
        "total_db_chunks": total_db_chunks,
        "estimated_total_hours": estimated_total_hours,
        "recommended_budget": recommended_chunk_budget,
    }


def main():
    parser = argparse.ArgumentParser(description="Knowledge Graph RAG Ingestion & Dry-Run CLI")
    parser.add_argument("--dry-run", action="store_true", help="Run benchmark dry-run on sampled chunks")
    parser.add_argument("--sample-size", type=int, default=20, help="Number of chunks to sample for dry-run")
    parser.add_argument("--subset", choices=["dev", "full"], default="dev", help="Corpus subset")
    parser.add_argument("--confirm", action="store_true", help="Confirm execution of full ingestion run")

    args = parser.parse_args()

    if args.dry_run:
        run_dry_run(sample_size=args.sample_size)
    else:
        print("Use --dry-run to benchmark throughput and measure compute budget.")


if __name__ == "__main__":
    main()
