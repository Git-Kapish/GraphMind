"""Unit tests for Neo4j graph query templates (PRD §10, Milestone M2.5/M5)."""

import pytest
from kgrag.graph.templates import (
    fetch_evidence_for_observations,
    query_neighbors,
    query_shared_neighbors,
)


def test_query_neighbors_finds_connected_entities():
    # Test on NVIDIA which has confirmed edges
    results = query_neighbors("nvidia")
    assert len(results) > 0

    relations = {r["relation"] for r in results}
    targets = {r["target"].lower() for r in results}

    assert any("santa clara" in t for t in targets) or any("worldwide" in t for t in targets)
    assert any("OPERATES_IN" in rel or "COMPETES_IN" in rel for rel in relations)


def test_query_shared_neighbors_finds_2hop_connections():
    results = query_shared_neighbors("nvidia", "microsoft")
    assert len(results) > 0

    shared_entities = {r["shared_entity"].lower() for r in results}
    assert "worldwide" in shared_entities or "computer hardware companies" in shared_entities


def test_fetch_evidence_for_observations_returns_quotes():
    results = query_neighbors("nvidia")
    obs_ids = []
    for r in results:
        obs_ids.extend(r.get("observation_ids", []))

    if obs_ids:
        quotes = fetch_evidence_for_observations(obs_ids[:5])
        assert len(quotes) > 0
        assert "evidence_quote" in quotes[0]
        assert "chunk_id" in quotes[0]
