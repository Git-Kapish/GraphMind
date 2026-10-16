"""Integration tests for FastAPI Query Endpoints and Baseline Endpoint (PRD §8, Milestone M7)."""

import httpx
import pytest

from kgrag.api.app import app
from kgrag.db.postgres import get_connection


@pytest.fixture
def test_client():
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=60.0)


@pytest.mark.asyncio
async def test_api_health_endpoint(test_client):
    """Verify /health returns 200 with component reachability and zero secret leakage (PRD §8)."""
    async with test_client as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert "postgres" in data["components"]
        assert "neo4j" in data["components"]
        assert "llm" in data["components"]

        # Secret leakage invariant check
        text = resp.text.lower()
        assert "password" not in text
        assert "secret" not in text


@pytest.mark.asyncio
async def test_get_entity_detail_existing(test_client):
    """Verify /entities/{entity_id} returns canonical metadata, degree, and relationships (PRD §8)."""
    # Fetch an existing canonical entity from database
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT entity_id, canonical_name FROM entities WHERE canonical_name ILIKE '%nvidia%' LIMIT 1;"
            )
            row = cur.fetchone()

    assert row is not None, "Need at least one entity in database"
    target_id = row["entity_id"]

    async with test_client as client:
        resp = await client.get(f"/entities/{target_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["entity_id"] == target_id
        assert "canonical_name" in data
        assert "degree" in data
        assert isinstance(data["relationships"], list)
        assert isinstance(data["absorbed_entities"], list)


@pytest.mark.asyncio
async def test_get_entity_detail_not_found(test_client):
    """Verify /entities/{entity_id} returns 404 for unknown entity ID (PRD §8)."""
    async with test_client as client:
        resp = await client.get("/entities/non_existent_entity_id_9999")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_chunk_detail_existing(test_client):
    """Verify /chunks/{chunk_id} returns authoritative text, filing metadata, and observations (PRD §8)."""
    # Fetch an existing chunk
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT chunk_id FROM chunks LIMIT 1;")
            row = cur.fetchone()

    assert row is not None, "Need at least one chunk in database"
    target_chunk_id = row["chunk_id"]

    async with test_client as client:
        resp = await client.get(f"/chunks/{target_chunk_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunk_id"] == target_chunk_id
        assert "company" in data
        assert "text" in data
        assert "section_path" in data
        assert "token_count" in data
        assert isinstance(data["observations"], list)


@pytest.mark.asyncio
async def test_get_chunk_detail_not_found(test_client):
    """Verify /chunks/{chunk_id} returns 404 for unknown chunk ID (PRD §8)."""
    async with test_client as client:
        resp = await client.get("/chunks/unknown_accession:item99:9999")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_query_input_validation(test_client):
    """Verify request validation: question length bounds and top_k bounds (PRD §8)."""
    async with test_client as client:
        # Question too short (< 3 chars)
        r1 = await client.post("/query", json={"question": "ab"})
        assert r1.status_code == 422

        # Question too long (> 500 chars)
        r2 = await client.post("/query", json={"question": "x" * 501})
        assert r2.status_code == 422

        # top_k out of bounds (< 1 or > 20)
        r3 = await client.post("/query", json={"question": "Valid question?", "top_k": 0})
        assert r3.status_code == 422

        r4 = await client.post("/query", json={"question": "Valid question?", "top_k": 25})
        assert r4.status_code == 422


@pytest.mark.asyncio
async def test_query_baseline_vector_retrieval(test_client):
    """Verify POST /query/baseline performs vector-only retrieval and returns PRD §8 schema."""
    async with test_client as client:
        resp = await client.post(
            "/query/baseline",
            json={
                "question": "What are the primary risk factors regarding supply chain disruptions for AMD?",
                "top_k": 3,
                "debug": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # Invariant checks
        assert data["route"]["chosen"] == "vector"
        assert data["route"]["fallback_used"] is False
        assert data["status"] in ("ok", "refused")
        assert data["validation"]["citation_resolution_passed"] is True
        assert len(data["graph_paths"]) == 0  # Baseline has NO graph paths
        assert len(data["passages"]) <= 3
        assert len(data["request_id"]) > 0

        # Citations check
        for cit in data["citations"]:
            assert cit["label"].startswith("P")
            assert len(cit["chunk_id"]) > 0
            assert cit["supports_claim"] in ("supported", "unsupported", "unknown")

        # Verify entry was recorded into routing_log
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM routing_log WHERE request_id = %s;", (data["request_id"],)
                )
                logged = cur.fetchone()
                assert logged is not None
                assert logged["route"] == "vector_baseline"


@pytest.mark.asyncio
async def test_query_auto_relational_graph(test_client):
    """Verify POST /query in auto mode routes relational questions to graph path with citations (PRD §8)."""
    async with test_client as client:
        resp = await client.post(
            "/query",
            json={
                "question": "Who are the executive officers of NVIDIA Corporation?",
                "mode": "auto",
                "top_k": 5,
                "debug": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # Invariants
        assert data["route"]["chosen"] in ("graph", "hybrid")
        assert data["status"] in ("ok", "refused")
        assert data["validation"]["citation_resolution_passed"] is True
        assert len(data["graph_paths"]) >= 1
        assert len(data["request_id"]) > 0

        # Citations check
        for cit in data["citations"]:
            assert cit["label"].startswith("G") or cit["label"].startswith("P")
            assert len(cit["chunk_id"]) > 0

        # Verify routing log
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM routing_log WHERE request_id = %s;", (data["request_id"],)
                )
                logged = cur.fetchone()
                assert logged is not None
                assert logged["route"] == data["route"]["chosen"]


@pytest.mark.asyncio
async def test_query_debug_flag_controls_payload_exposure(test_client):
    """Verify that internal evidence and passages are omitted when debug=False (PRD §8)."""
    async with test_client as client:
        resp_no_debug = await client.post(
            "/query",
            json={
                "question": "Who are the executive officers of NVIDIA Corporation?",
                "mode": "graph",
                "debug": False,
            },
        )
        assert resp_no_debug.status_code == 200
        data = resp_no_debug.json()
        assert data["graph_paths"] == []
        assert data["passages"] == []
