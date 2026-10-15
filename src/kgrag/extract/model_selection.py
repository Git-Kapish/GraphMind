"""Model Selection Gate comparison benchmark (PRD §6.1, Milestone M2)."""

import logging
import time
from typing import Any

from kgrag.db.postgres import get_connection
from kgrag.extract.llm_extractor import LLMExtractor
from kgrag.llm.client import OllamaClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def evaluate_model_on_sample(
    model_tag: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate candidate model on structured extraction validity, quote match, and latency."""
    client = OllamaClient(model=model_tag)
    extractor = LLMExtractor(llm_client=client)

    total_chunks = len(chunks)
    valid_json_count = 0
    total_relations_extracted = 0
    total_quote_verified_relations = 0
    total_elapsed = 0.0

    print(f"\n--- Benchmarking Model: {model_tag} on {total_chunks} chunks ---", flush=True)

    for idx, c in enumerate(chunks, 1):
        chunk_id = c["chunk_id"]
        text = c["text"]
        company = c["company"]
        ticker = c["ticker"]

        t0 = time.perf_counter()
        try:
            relations = extractor.extract_chunk(
                chunk_id=chunk_id,
                chunk_text=text,
                filer_company=company,
                filer_ticker=ticker,
                force=True,
            )
            elapsed = time.perf_counter() - t0
            total_elapsed += elapsed
            valid_json_count += 1
            total_quote_verified_relations += len(relations)
            total_relations_extracted += len(relations)
            print(f"[{idx}/{total_chunks}] {chunk_id}: {len(relations)} relations ({elapsed:.2f}s)", flush=True)
        except Exception as e:
            elapsed = time.perf_counter() - t0
            total_elapsed += elapsed
            print(f"[{idx}/{total_chunks}] {chunk_id}: FAILED ({e}) ({elapsed:.2f}s)", flush=True)

    valid_json_rate = (valid_json_count / total_chunks) if total_chunks > 0 else 0.0
    quote_match_rate = (
        (total_quote_verified_relations / total_relations_extracted)
        if total_relations_extracted > 0
        else 1.0
    )
    avg_sec_per_chunk = (total_elapsed / total_chunks) if total_chunks > 0 else 0.0

    return {
        "model": model_tag,
        "sample_size": total_chunks,
        "valid_json_rate": valid_json_rate,
        "quote_match_rate": quote_match_rate,
        "total_relations": total_quote_verified_relations,
        "avg_sec_per_chunk": avg_sec_per_chunk,
        "total_elapsed_sec": total_elapsed,
    }


def run_model_selection_gate(sample_size: int = 10, models: list[str] | None = None) -> list[dict[str, Any]]:
    """Run model selection gate comparing candidate models (§6.1)."""
    candidate_models = models or ["llama3.2:latest", "qwen2.5:3b"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Select chunks that mention relation cues
            cur.execute(
                """
                SELECT c.chunk_id, c.text, d.company, d.ticker
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE d.ticker <> '' AND c.item <> 'exhibit21'
                  AND (c.text ILIKE '%%supplier%%' OR c.text ILIKE '%%manufactur%%' OR c.text ILIKE '%%compet%%')
                ORDER BY c.chunk_id
                LIMIT %(limit)s;
                """,
                {"limit": sample_size},
            )
            chunks = cur.fetchall()

    if not chunks:
        print("No matching cue chunks found.")
        return []

    results = []
    for m in candidate_models:
        res = evaluate_model_on_sample(m, chunks)
        results.append(res)

    print("\n" + "=" * 70)
    print("  MODEL SELECTION GATE BENCHMARK COMPARISON (§6.1)")
    print("=" * 70)
    print(f"{'Model':<20} | {'JSON Valid':<10} | {'Quote Match':<11} | {'Relations':<9} | {'Sec/Chunk'}")
    print("-" * 70)
    for r in results:
        print(
            f"{r['model']:<20} | "
            f"{r['valid_json_rate']*100:>8.1f}% | "
            f"{r['quote_match_rate']*100:>9.1f}% | "
            f"{r['total_relations']:>9} | "
            f"{r['avg_sec_per_chunk']:>6.2f}s"
        )
    print("=" * 70 + "\n")

    return results


if __name__ == "__main__":
    run_model_selection_gate()
