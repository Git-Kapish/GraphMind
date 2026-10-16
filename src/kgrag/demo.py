"""Interactive & Automated Demonstration for Knowledge Graph RAG API & Baseline (PRD §8, §14).

Usage:
    uv run python -m kgrag.demo               # Interactive CLI menu or automated showcase
    uv run python -m kgrag.demo --showcase    # Non-interactive complete automated showcase
"""

import argparse
import time

from kgrag.api.app import app
from kgrag.db.postgres import get_connection


def print_banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str) -> None:
    print("\n" + "-" * 80)
    print(f">> {title}")
    print("-" * 80)


def run_showcase() -> None:
    """Run the complete automated showcase across all API endpoints."""
    print_banner("KNOWLEDGE GRAPH RAG - API & BASELINE DEMONSTRATION")
    print("Local-first hybrid Knowledge Graph & Vector RAG over Enterprise SEC 10-K Filings.")
    print(
        "Zero model spend ($0) via local Ollama (qwen2.5:3b + nomic-embed-text) & pgvector + Neo4j."
    )

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        # -------------------------------------------------------------------
        # 1. HEALTH ENDPOINT (PRD §8)
        # -------------------------------------------------------------------
        print_section("1. HEALTH REACHABILITY ENDPOINT (GET /health)")
        resp = client.get("/health")
        print(f"Status Code: {resp.status_code}")
        health_data = resp.json()
        print(f"Overall Service Status : {health_data['status'].upper()}")
        print(f"Timestamp              : {health_data['timestamp']}")
        print(f"API Version            : {health_data['version']}")
        print("\nComponent Breakdown:")
        for comp, details in health_data["components"].items():
            print(f"  - {comp:<10} : status={details['status']}, details={details['details']}")

        # -------------------------------------------------------------------
        # 2. CANONICAL ENTITY PROVENANCE (GET /entities/{entity_id})
        # -------------------------------------------------------------------
        print_section("2. CANONICAL ENTITY & TOPOLOGY LOOKUP (GET /entities/{entity_id})")
        # Find a known entity ID
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT entity_id, canonical_name FROM entities WHERE canonical_name ILIKE '%nvidia%' LIMIT 1;"
                )
                ent_row = cur.fetchone()

        if ent_row:
            eid = ent_row["entity_id"]
            resp = client.get(f"/entities/{eid}")
            print(f"Status Code: {resp.status_code}")
            ent_data = resp.json()
            print(f"Entity ID        : {ent_data['entity_id']}")
            print(f"Canonical Name   : {ent_data['canonical_name']}")
            print(f"Type             : {ent_data['type']}")
            print(f"Aliases          : {ent_data['aliases']}")
            print(f"Neo4j Degree     : {ent_data['degree']}")
            print(f"Absorbed Aliases : {ent_data['absorbed_entities']}")
            print(f"Relationships    : {len(ent_data['relationships'])} relationships retrieved")
            for rel in ent_data["relationships"][:3]:
                print(
                    f"  * -[{rel.get('relation')}]-> {rel.get('target_name')} ({rel.get('target_id')})"
                )

        # Negative test (404)
        resp_404 = client.get("/entities/non_existent_entity_9999")
        print(
            f"\nNegative Test (non-existent entity ID): HTTP {resp_404.status_code} -> {resp_404.json()['detail']}"
        )

        # -------------------------------------------------------------------
        # 3. AUTHORITATIVE CHUNK PROVENANCE (GET /chunks/{chunk_id})
        # -------------------------------------------------------------------
        print_section("3. AUTHORITATIVE CHUNK & OBSERVATIONS LOOKUP (GET /chunks/{chunk_id})")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT chunk_id FROM chunks WHERE chunk_id LIKE '%exhibit21%' LIMIT 1;"
                )
                chunk_row = cur.fetchone()

        if chunk_row:
            cid = chunk_row["chunk_id"]
            resp = client.get(f"/chunks/{cid}")
            print(f"Status Code: {resp.status_code}")
            cdata = resp.json()
            print(f"Chunk ID      : {cdata['chunk_id']}")
            print(f"Company       : {cdata['company']} ({cdata['ticker']})")
            print(f"Form / Year   : {cdata['form_type']} {cdata['fiscal_year']}")
            print(f"Accession     : {cdata['accession']}")
            print(f"Section Path  : {cdata['section_path']} (Item {cdata['item']})")
            print(f"Token Count   : {cdata['token_count']}")
            print(
                f"Observations  : {cdata['observations_count']} verified extraction observations attached"
            )
            for obs in cdata["observations"][:2]:
                print(
                    f"  * ({obs['head_surface']}) -[{obs['relation_type']}]-> ({obs['tail_surface']})"
                )
                print(f'    Evidence Quote: "{obs["evidence_quote"][:90]}..."')

        # Negative test (404)
        resp_c404 = client.get("/chunks/unknown:item99:9999")
        print(
            f"\nNegative Test (non-existent chunk ID): HTTP {resp_c404.status_code} -> {resp_c404.json()['detail']}"
        )

        # -------------------------------------------------------------------
        # 4. BASELINE VECTOR RAG ENDPOINT (POST /query/baseline)
        # -------------------------------------------------------------------
        print_section("4. SYSTEM A: PLAIN VECTOR RAG BASELINE (POST /query/baseline)")
        q_baseline = "What are the primary risk factors regarding supply chain disruptions for AMD?"
        print(f'Query: "{q_baseline}"')
        t0 = time.perf_counter()
        resp = client.post(
            "/query/baseline", json={"question": q_baseline, "top_k": 3, "debug": True}
        )
        elapsed = time.perf_counter() - t0
        print(f"HTTP Status: {resp.status_code} (in {elapsed:.2f}s)")
        b_data = resp.json()
        print(
            f"Route Chosen       : {b_data['route']['chosen'].upper()} (confidence={b_data['route']['confidence']})"
        )
        print(f"Response Status    : {b_data['status']}")
        print(
            f"Citation Invariant : {b_data['validation']['citation_resolution_passed']} (attempts={b_data['validation']['attempts']})"
        )
        print(
            f"Latency Breakdown  : route={b_data['latency_ms']['route']}ms, retrieve={b_data['latency_ms']['retrieve']}ms, generate={b_data['latency_ms']['generate']}ms, total={b_data['latency_ms']['total']}ms"
        )
        print(f"Passages Retrieved : {len(b_data['passages'])} chunks")
        print(f"Answer:\n{b_data['answer']}\n")
        print("Citations Resolved:")
        for cit in b_data["citations"]:
            print(
                f"  [{cit['label']}] Chunk: {cit['chunk_id']} | Doc: {cit['doc']} | Section: {cit['section']}"
            )
            print(f'       Snippet: "{cit["snippet"][:110]}..."')

        # -------------------------------------------------------------------
        # 5. AUTO-ROUTED HYBRID / GRAPH RAG (POST /query)
        # -------------------------------------------------------------------
        print_section("5. AUTO-ROUTED GRAPH / HYBRID RAG (POST /query)")
        q_graph = "Who are the executive officers of NVIDIA Corporation?"
        print(f"Query: \"{q_graph}\" (mode='auto')")
        t0 = time.perf_counter()
        resp = client.post(
            "/query", json={"question": q_graph, "mode": "auto", "top_k": 5, "debug": True}
        )
        elapsed = time.perf_counter() - t0
        print(f"HTTP Status: {resp.status_code} (in {elapsed:.2f}s)")
        q_data = resp.json()
        print(
            f"Route Chosen       : {q_data['route']['chosen'].upper()} (confidence={q_data['route']['confidence']})"
        )
        print(f"Fallback Used      : {q_data['route']['fallback_used']}")
        print(f"Response Status    : {q_data['status']}")
        print(
            f"Citation Invariant : {q_data['validation']['citation_resolution_passed']} (attempts={q_data['validation']['attempts']})"
        )
        print(f"Graph Paths Count  : {len(q_data['graph_paths'])}")
        print(
            f"Latency Breakdown  : route={q_data['latency_ms']['route']}ms, retrieve={q_data['latency_ms']['retrieve']}ms, generate={q_data['latency_ms']['generate']}ms, total={q_data['latency_ms']['total']}ms"
        )
        print(f"Answer:\n{q_data['answer']}\n")
        print("Citations Resolved:")
        for cit in q_data["citations"]:
            print(
                f"  [{cit['label']}] Chunk: {cit['chunk_id']} | Doc: {cit['doc']} | Section: {cit['section']}"
            )
            print(f'       Snippet: "{cit["snippet"][:110]}..."')

        # -------------------------------------------------------------------
        # 6. ROUTING AUDIT LOG VERIFICATION (PostgreSQL routing_log)
        # -------------------------------------------------------------------
        print_section("6. ROUTING DECISION AUDIT TRAIL (PostgreSQL routing_log)")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, ts, question, route, confidence, fallback_used, outcome, latency_ms, request_id "
                    "FROM routing_log ORDER BY id DESC LIMIT 5;"
                )
                rows = cur.fetchall()

        print(
            f"{'ID':<4} | {'ROUTE':<16} | {'CONF':<5} | {'FALLBACK':<8} | {'STATUS':<15} | {'LATENCY':<8} | {'QUESTION'}"
        )
        print("-" * 95)
        for r in rows:
            q_snip = r["question"][:35] + ("..." if len(r["question"]) > 35 else "")
            print(
                f"{r['id']:<4} | {r['route']:<16} | {r['confidence'] or 0.0:<5.2f} | {str(r['fallback_used']):<8} | {r['outcome']:<15} | {r['latency_ms']}ms | {q_snip}"
            )

    print_banner("MILESTONE M7 SHOWCASE COMPLETE - ALL ENDPOINTS OPERATIONAL")


def interactive_mode() -> None:
    """Interactive loop for testing custom questions across baseline, graph, vector, and hybrid modes."""
    print_banner("KNOWLEDGE GRAPH RAG - INTERACTIVE QUERY TESTER")
    print(
        "Test any query against the API with real-time routing, generation, and citation validation."
    )
    print("Type 'exit' or 'quit' to return to menu.\n")

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        while True:
            try:
                question = input("\nEnter your question: ").strip()
                if not question:
                    continue
                if question.lower() in ("exit", "quit", "q"):
                    break

                print("\nChoose mode:")
                print("  [1] auto (Router automatically selects graph, vector, or hybrid)")
                print("  [2] baseline (System A: Pure vector RAG baseline)")
                print("  [3] graph (Graph traversal only)")
                print("  [4] vector (Vector similarity only)")
                print("  [5] hybrid (Both graph paths and vector passages)")
                mode_choice = input("Select mode (1-5, default 1): ").strip()

                mode_map = {
                    "1": "auto",
                    "2": "baseline",
                    "3": "graph",
                    "4": "vector",
                    "5": "hybrid",
                }
                mode = mode_map.get(mode_choice, "auto")

                print(f"\n[Executing query with mode='{mode}'...]")
                t0 = time.perf_counter()

                if mode == "baseline":
                    resp = client.post(
                        "/query/baseline", json={"question": question, "top_k": 5, "debug": True}
                    )
                else:
                    resp = client.post(
                        "/query",
                        json={"question": question, "mode": mode, "top_k": 5, "debug": True},
                    )

                elapsed = time.perf_counter() - t0

                if resp.status_code != 200:
                    print(f"Error {resp.status_code}: {resp.text}")
                    continue

                data = resp.json()
                print(f"\n--- QUERY RESPONSE (HTTP {resp.status_code} in {elapsed:.2f}s) ---")
                print(
                    f"Route Chosen       : {data['route']['chosen'].upper()} (conf={data['route']['confidence']}, fallback={data['route']['fallback_used']})"
                )
                print(f"Status             : {data['status']}")
                print(
                    f"Citation Invariant : {data['validation']['citation_resolution_passed']} (attempts={data['validation']['attempts']})"
                )
                print(
                    f"Latency Breakdown  : route={data['latency_ms']['route']}ms, retrieve={data['latency_ms']['retrieve']}ms, generate={data['latency_ms']['generate']}ms, total={data['latency_ms']['total']}ms"
                )
                print(f"\nAnswer:\n{data['answer']}\n")

                if data["citations"]:
                    print("Citations:")
                    for cit in data["citations"]:
                        print(
                            f"  [{cit['label']}] Chunk: {cit['chunk_id']} | Doc: {cit['doc']} | Section: {cit['section']}"
                        )
                        print(f'       Snippet: "{cit["snippet"][:120]}..."')
                else:
                    print("Citations: <none>")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Knowledge Graph RAG API Showcase & Interactive Tester"
    )
    parser.add_argument(
        "--showcase", action="store_true", help="Run automated capability showcase and exit"
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Launch interactive query tester"
    )
    args = parser.parse_args()

    if args.showcase:
        run_showcase()
        return

    if args.interactive:
        interactive_mode()
        return

    # Default menu
    print_banner("KNOWLEDGE GRAPH RAG - DEMO MENU")
    print("1. Run complete automated API capability showcase")
    print("2. Launch interactive question testing CLI")
    print("3. Exit")
    choice = input("\nSelect an option (1-3): ").strip()
    if choice == "1":
        run_showcase()
    elif choice == "2":
        interactive_mode()
    else:
        print("Exiting.")


if __name__ == "__main__":
    main()
