"""Unit tests for the GraphMind CLI (Click + Rich interface)."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kgrag.cli import cli


def test_cli_help():
    """Verify CLI root help message displays correctly."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "GraphMind: Local-first Knowledge Graph RAG" in result.output
    assert "query" in result.output
    assert "compare" in result.output
    assert "entity" in result.output
    assert "chunk" in result.output
    assert "health" in result.output


def test_query_cmd_formatted():
    """Verify one-shot query formatting with citations and route pill."""
    runner = CliRunner()
    mock_resp = {
        "answer": "NVIDIA is a leader in accelerated computing [P1].",
        "citations": [
            {
                "label": "P1",
                "chunk_id": "nvda-001",
                "doc": "NVDA 10-K",
                "section": "Item 1. Business",
                "snippet": "We specialize in GPUs and accelerated computing architectures.",
                "supports_claim": "supported",
            }
        ],
        "route": {"chosen": "hybrid", "confidence": 0.95, "fallback_used": False},
        "graph_paths": [
            {
                "head_entity": "NVIDIA",
                "relation_type": "OPERATES_IN",
                "tail_entity": "Accelerated Computing",
                "observation_id": "obs-1",
                "chunk_id": "nvda-001",
            }
        ],
        "passages": [],
        "validation": {"citation_resolution_passed": True, "attempts": 1},
        "status": "ok",
        "latency_ms": {"route": 12, "retrieve": 45, "generate": 500, "total": 557},
    }

    with patch("kgrag.cli.QueryClient.query", return_value=mock_resp):
        result = runner.invoke(cli, ["query", "What does NVIDIA specialize in?"])
        assert result.exit_code == 0
        assert "Grounded Answer" in result.output
        assert "NVIDIA is a leader in accelerated computing" in result.output
        assert "HYBRID" in result.output
        assert "PASSED (100% citations resolved to corpus)" in result.output
        assert "Supporting Citations" in result.output
        assert "nvda-001" in result.output


def test_query_cmd_json():
    """Verify --json flag outputs pure valid JSON."""
    runner = CliRunner()
    mock_resp = {
        "answer": "Test answer [P1].",
        "citations": [],
        "route": {"chosen": "vector", "confidence": 0.88, "fallback_used": False},
        "graph_paths": [],
        "passages": [],
        "validation": {"citation_resolution_passed": True, "attempts": 1},
        "status": "ok",
        "latency_ms": {"route": 5, "retrieve": 10, "generate": 200, "total": 215},
    }

    with patch("kgrag.cli.QueryClient.query", return_value=mock_resp):
        result = runner.invoke(cli, ["query", "Test query", "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["answer"] == "Test answer [P1]."
        assert parsed["route"]["chosen"] == "vector"


def test_compare_cmd():
    """Verify side-by-side A/B comparison formatting."""
    runner = CliRunner()
    mock_hybrid = {
        "answer": "Hybrid GraphMind grounded answer [G1].",
        "citations": [
            {"label": "G1", "chunk_id": "c1", "doc": "Doc1", "section": "Sec1", "snippet": "..."}
        ],
        "route": {"chosen": "hybrid", "confidence": 0.92, "fallback_used": False},
        "graph_paths": [{"head_entity": "A", "relation_type": "B", "tail_entity": "C"}],
        "passages": [{"ticker": "NVDA", "score": 0.85, "chunk_id": "c1", "text": "..."}],
        "validation": {"citation_resolution_passed": True, "attempts": 1},
        "latency_ms": {"total": 850},
    }
    mock_base = {
        "answer": "Baseline plain vector answer [P1].",
        "citations": [
            {"label": "P1", "chunk_id": "c2", "doc": "Doc2", "section": "Sec2", "snippet": "..."}
        ],
        "route": {"chosen": "vector", "confidence": 1.0, "fallback_used": False},
        "graph_paths": [],
        "passages": [{"ticker": "NVDA", "score": 0.72, "chunk_id": "c2", "text": "..."}],
        "validation": {"citation_resolution_passed": True, "attempts": 1},
        "latency_ms": {"total": 600},
    }

    with (
        patch("kgrag.cli.QueryClient.query", return_value=mock_hybrid),
        patch("kgrag.cli.QueryClient.query_baseline", return_value=mock_base),
    ):
        result = runner.invoke(cli, ["compare", "What is the relation between A and C?"])
        assert result.exit_code == 0
        assert "A/B SYSTEM COMPARISON" in result.output
        assert "System C: GraphMind Hybrid Answer" in result.output
        assert "System A: Vector Baseline Answer" in result.output


def test_entity_cmd():
    """Verify entity topology lookup and relationship formatting."""
    runner = CliRunner()
    mock_entity = {
        "canonical_name": "Apple Inc.",
        "entity_id": "apple-001",
        "type": "Company",
        "degree": 5,
        "aliases": ["Apple Computer", "AAPL"],
        "relationships": [
            {
                "direction": "outgoing",
                "rel_type": "MANUFACTURES",
                "target_name": "iPhone",
                "target_id": "iphone-01",
            }
        ],
    }

    with patch("kgrag.cli.QueryClient.get_entity", return_value=mock_entity):
        result = runner.invoke(cli, ["entity", "Apple Inc."])
        assert result.exit_code == 0
        assert "Canonical Entity Details" in result.output
        assert "Apple Inc." in result.output
        assert "apple-001" in result.output
        assert "MANUFACTURES" in result.output
        assert "iPhone" in result.output


def test_chunk_cmd():
    """Verify chunk document metadata and verbatim text formatting."""
    runner = CliRunner()
    mock_chunk = {
        "chunk_id": "chk-12345",
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "form_type": "10-K",
        "fiscal_year": 2024,
        "section_path": "Item 1. Business",
        "text": "Apple designs and markets mobile devices and services.",
        "observations": [
            {
                "head_surface": "Apple",
                "relation_type": "DESIGNS",
                "tail_surface": "mobile devices",
                "evidence_quote": "Apple designs and markets...",
                "evidence_verified": True,
            }
        ],
    }

    with patch("kgrag.cli.QueryClient.get_chunk", return_value=mock_chunk):
        result = runner.invoke(cli, ["chunk", "chk-12345"])
        assert result.exit_code == 0
        assert "Chunk SEC Document Provenance" in result.output
        assert "chk-12345" in result.output
        assert "AAPL" in result.output
        assert "Authoritative Verbatim Text" in result.output
        assert "Extracted Knowledge Graph Observations" in result.output
        assert "DESIGNS" in result.output


def test_health_cmd():
    """Verify health command output."""
    runner = CliRunner()
    mock_health = {
        "status": "ok",
        "version": "0.1.0",
        "components": {
            "postgres": {"status": "healthy", "details": {"pgvector_installed": True}},
            "neo4j": {"status": "healthy", "details": {"edition": "community"}},
            "llm": {"status": "healthy", "details": {"model_available": True}},
        },
    }

    with patch("kgrag.cli.QueryClient.get_health", return_value=mock_health):
        result = runner.invoke(cli, ["health"])
        assert result.exit_code == 0
        assert "Overall Service Status: OK" in result.output
        assert "postgres" in result.output
        assert "neo4j" in result.output
        assert "llm" in result.output


def test_interactive_help_and_exit():
    """Verify REPL help command and clean exit."""
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.mode_description = "Local In-Process"

    with patch("kgrag.cli.QueryClient", return_value=mock_client):
        result = runner.invoke(cli, ["interactive"], input="/help\nexit\n")
        assert result.exit_code == 0
        assert "GraphMind Interactive CLI Commands" in result.output
        assert "Goodbye!" in result.output
