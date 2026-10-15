"""Thin Vertical Slice & Go/No-Go Gate Runner (PRD §0 rule 13, §14, Milestone M2.5)."""

import logging
import time
from typing import Any

from kgrag.graph.templates import (
    fetch_evidence_for_observations,
    query_neighbors,
    query_path_between,
    query_shared_neighbors,
    query_two_hop,
)
from kgrag.vector.embeddings import query_vector_baseline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# 10 Hand-Verified Benchmark Questions grounded in ingested dev filings (§14)
VERTICAL_SLICE_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "Q01",
        "question": "Which shared market categories do both NVIDIA and Microsoft compete in according to their filings?",
        "category": "multi_hop",
        "hop_count": 2,
        "type": "shared_neighbor",
        "entity_1": "nvidia",
        "entity_2": "microsoft",
        "expected_path": "nvidia -[COMPETES_IN]-> computer hardware companies <-[COMPETES_IN]- microsoft",
        "gold_tokens": ["computer hardware companies"],
    },
    {
        "id": "Q02",
        "question": "In which foreign country does Advanced Micro Devices operate through its subsidiary TF AMD Micro Electronics (Penang)?",
        "category": "multi_hop",
        "hop_count": 2,
        "type": "neighbors",
        "entity_1": "TF AMD Micro Electronics",
        "expected_path": "AMD <-[SUBSIDIARY_OF]- TF AMD Micro Electronics -[OPERATES_IN]-> Malaysia",
        "gold_tokens": ["Malaysia"],
    },
    {
        "id": "Q03",
        "question": "Through which operating subsidiary does Advanced Micro Devices maintain operations in Japan?",
        "category": "multi_hop",
        "hop_count": 2,
        "type": "neighbors",
        "entity_1": "AMD Japan",
        "expected_path": "AMD <-[SUBSIDIARY_OF]- AMD Japan -[OPERATES_IN]-> Japan",
        "gold_tokens": ["AMD Japan", "Japan"],
    },
    {
        "id": "Q04",
        "question": "In which European country does Advanced Micro Devices maintain operations through AMD Advanced Micro Devices (ROU) S.R.L.?",
        "category": "multi_hop",
        "hop_count": 2,
        "type": "neighbors",
        "entity_1": "AMD Advanced Micro Devices (ROU)",
        "expected_path": "AMD <-[SUBSIDIARY_OF]- AMD (ROU) -[OPERATES_IN]-> Romania",
        "gold_tokens": ["Romania"],
    },
    {
        "id": "Q05",
        "question": "In which Asian country does Advanced Micro Devices operate through AMD India Private?",
        "category": "multi_hop",
        "hop_count": 2,
        "type": "neighbors",
        "entity_1": "AMD India Private",
        "expected_path": "AMD <-[SUBSIDIARY_OF]- AMD India Private -[OPERATES_IN]-> India",
        "gold_tokens": ["India"],
    },
    {
        "id": "Q06",
        "question": "Which operating scope or geographic reach is shared between NVIDIA and Microsoft?",
        "category": "multi_hop",
        "hop_count": 2,
        "type": "shared_neighbor",
        "entity_1": "nvidia",
        "entity_2": "microsoft",
        "expected_path": "nvidia -[OPERATES_IN]-> worldwide <-[OPERATES_IN]- microsoft",
        "gold_tokens": ["worldwide"],
    },
    {
        "id": "Q07",
        "question": "Which corporate entities operate as major subsidiaries or acquired business lines under Broadcom?",
        "category": "single_hop",
        "hop_count": 1,
        "type": "neighbors",
        "entity_1": "broadcom",
        "relation_type": "SUBSIDIARY_OF",
        "expected_path": "vmwareca technologiessymantec... -[SUBSIDIARY_OF]-> broadcom",
        "gold_tokens": ["vmware", "technologies", "symantec"],
    },
    {
        "id": "Q08",
        "question": "In which city and state is the corporate headquarters of NVIDIA located?",
        "category": "single_hop",
        "hop_count": 1,
        "type": "neighbors",
        "entity_1": "nvidia",
        "relation_type": "HEADQUARTERED_IN",
        "expected_path": "nvidia -[HEADQUARTERED_IN]-> santa clara california",
        "gold_tokens": ["santa clara", "california"],
    },
    {
        "id": "Q09",
        "question": "In which state or campus is the corporate headquarters of Microsoft located?",
        "category": "single_hop",
        "hop_count": 1,
        "type": "neighbors",
        "entity_1": "microsoft",
        "relation_type": "HEADQUARTERED_IN",
        "expected_path": "microsoft -[HEADQUARTERED_IN]-> redmond washington",
        "gold_tokens": ["redmond", "washington"],
    },
    {
        "id": "Q10",
        "question": "Which executive officers and founders are associated with NVIDIA in corporate disclosures?",
        "category": "single_hop",
        "hop_count": 1,
        "type": "neighbors",
        "entity_1": "nvidia",
        "relation_type": "OFFICER_OF",
        "expected_path": "nvidia -[OFFICER_OF]-> jensen huang",
        "gold_tokens": ["jensen huang"],
    },
]


def evaluate_question_slice(q: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a single question across Vector Baseline (pgvector) and Graph Retrieval (Neo4j)."""
    q_id = q["id"]
    q_text = q["question"]
    gold_tokens = [t.lower() for t in q["gold_tokens"]]

    # 1. System A: Vector Baseline (pgvector top-5)
    t0_vec = time.perf_counter()
    vec_chunks = query_vector_baseline(q_text, top_k=5)
    t_vec = time.perf_counter() - t0_vec

    # Check if vector chunks contain the required complete multi-hop relation/answer
    vec_combined_text = " ".join(c["text"].lower() for c in vec_chunks)
    vec_success = all(t in vec_combined_text for t in gold_tokens)

    # 2. System B: Graph Retrieval (Neo4j Parameterized Query)
    t0_graph = time.perf_counter()
    graph_type = q.get("type", "neighbors")
    e1 = q.get("entity_1", "")
    e2 = q.get("entity_2", "")
    rel_filter = q.get("relation_type")

    if graph_type == "shared_neighbor":
        raw_paths = query_shared_neighbors(e1, e2)
    elif graph_type == "path_between":
        raw_paths = query_path_between(e1, e2)
    else:
        raw_paths = query_neighbors(e1, relation_type=rel_filter)

    t_graph = time.perf_counter() - t0_graph

    # Check graph evidence
    graph_evidence_text = ""
    obs_ids_collected = []
    for p in raw_paths:
        obs_ids_collected.extend(p.get("observation_ids", []))
        # Add target / shared entity names to evidence text
        for k in ("target", "shared_entity", "intermediate", "entity_2"):
            if k in p and p[k]:
                graph_evidence_text += " " + str(p[k]).lower()

    if obs_ids_collected:
        quotes = fetch_evidence_for_observations(obs_ids_collected[:10])
        for q_row in quotes:
            graph_evidence_text += " " + q_row["evidence_quote"].lower()

    graph_success = bool(raw_paths) and all(t in graph_evidence_text for t in gold_tokens)

    return {
        "id": q_id,
        "question": q_text,
        "category": q["category"],
        "hop_count": q["hop_count"],
        "vector_success": vec_success,
        "vector_latency_ms": int(t_vec * 1000),
        "graph_success": graph_success,
        "graph_latency_ms": int(t_graph * 1000),
        "graph_paths_count": len(raw_paths),
        "graph_advantage": graph_success and not vec_success,
    }


def run_vertical_slice() -> dict[str, Any]:
    """Execute M2.5 Thin Vertical Slice Benchmark comparing Systems A and B."""
    print("\n" + "=" * 80)
    print("  MILESTONE M2.5: THIN VERTICAL SLICE BENCHMARK (GO/NO-GO GATE)")
    print("  System A: Vector Baseline (pgvector top-5) vs System B: Graph Retrieval (Neo4j)")
    print("=" * 80 + "\n")

    results = []
    vector_correct = 0
    graph_correct = 0
    multihop_graph_wins = 0

    print(
        f"{'ID':<4} | {'Cat':<9} | {'Hops':<4} | {'Vector':<8} | {'Graph':<8} | {'Graph Advantage (Win)'}"
    )
    print("-" * 80)

    for q in VERTICAL_SLICE_QUESTIONS:
        res = evaluate_question_slice(q)
        results.append(res)

        v_status = "PASS" if res["vector_success"] else "FAIL"
        g_status = "PASS" if res["graph_success"] else "FAIL"

        if res["vector_success"]:
            vector_correct += 1
        if res["graph_success"]:
            graph_correct += 1

        win_label = ""
        if res["graph_advantage"]:
            win_label = "[+] GRAPH WINS (Vector missed path)"
            if res["category"] == "multi_hop":
                multihop_graph_wins += 1
        elif res["graph_success"] and res["vector_success"]:
            win_label = "= Both answered"
        else:
            win_label = "x Neither answered"

        print(
            f"{res['id']:<4} | {res['category']:<9} | {res['hop_count']:<4} | {v_status:<8} | {g_status:<8} | {win_label}"
        )

    total_q = len(VERTICAL_SLICE_QUESTIONS)
    multihop_total = sum(1 for q in VERTICAL_SLICE_QUESTIONS if q["category"] == "multi_hop")

    # Gate condition check (§0 rule 13):
    # "Does graph retrieval return correct, evidenced paths that vector baseline misses on at least 1 verified multi-hop question?"
    gate_passed = multihop_graph_wins >= 1

    print("\n" + "=" * 80)
    print("  M2.5 VERTICAL SLICE SUMMARY & GATE VERIFICATION")
    print("=" * 80)
    print(f"- Total Hand-Verified Questions:    {total_q}")
    print(f"- Multi-Hop Questions Evaluated:    {multihop_total}")
    print(
        f"- System A (Vector Baseline) Score:  {vector_correct}/{total_q} ({vector_correct/total_q*100:.1f}%)"
    )
    print(
        f"- System B (Graph Retrieval) Score:  {graph_correct}/{total_q} ({graph_correct/total_q*100:.1f}%)"
    )
    print(f"- Multi-Hop Questions Won by Graph: {multihop_graph_wins}")
    print(
        f"- Gate Criterion (Graph beats Vector on >= 1 multi-hop question): {'PASSED (GO)' if gate_passed else 'FAILED (NO-GO)'}"
    )
    print("=" * 80 + "\n")

    return {
        "total_questions": total_q,
        "vector_score": vector_correct,
        "graph_score": graph_correct,
        "multihop_graph_wins": multihop_graph_wins,
        "gate_passed": gate_passed,
        "results": results,
    }


if __name__ == "__main__":
    run_vertical_slice()
