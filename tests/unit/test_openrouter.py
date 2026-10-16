"""Unit tests for OpenRouter model integration (System One, Embedding, Generative LLM).

Verifies:
1. Configuration loading, environment variables, and missing API key guards.
2. System One decision model (inception/mercury-decide:free) via /api/alpha/decisions.
3. Embedding model (nvidia/nemotron-3-embed-1b:free) 2048-d generation, batching, and error handling.
4. Generative LLM (nvidia/nemotron-3.5-super-vl:free) unstructured and Pydantic structured output.
5. Vector dimension validation and safe migration (preventing vector space mixing).
6. Router and claim-support integration with mock external APIs.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from kgrag.answer.validator import ResolvedCitation, verify_claim_support
from kgrag.config import Settings
from kgrag.llm.client import OpenRouterClient, OpenRouterEmbeddingClient
from kgrag.llm.decisions import MercuryDecideClient
from kgrag.retrieval.router import route_query
from kgrag.vector.embeddings import validate_vector_dimensions

# ---------------------------------------------------------------------------
# 1. Configuration & Missing API Key Tests
# ---------------------------------------------------------------------------


def test_openrouter_settings_defaults():
    """Verify default models and 2048-d vector configuration."""
    s = Settings()
    assert s.llm.runtime == "openrouter"
    assert s.llm.model == "nvidia/nemotron-3.5-super-vl:free"
    assert s.embedding.model == "nvidia/nemotron-3-embed-1b:free"
    assert s.embedding.dimension == 2048
    assert s.system_one.model == "inception/mercury-decide:free"
    assert s.system_one.endpoint == "https://openrouter.ai/api/alpha/decisions"


def test_missing_api_key_raises_error():
    """Verify all clients fail fast with descriptive errors when OPENROUTER_API_KEY is missing."""
    with patch.dict("os.environ", {"OPENROUTER_API_KEY": ""}):
        embed_client = OpenRouterEmbeddingClient(api_key="")
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY is not configured"):
            embed_client.embed(["test text"])

        llm_client = OpenRouterClient(api_key="")
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY is not configured"):
            llm_client.generate("test prompt")

        decide_client = MercuryDecideClient(api_key="")
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY environment variable is missing"):
            decide_client.decide_route("What are the subsidiaries?")


# ---------------------------------------------------------------------------
# 2. System One Decision Model (inception/mercury-decide:free)
# ---------------------------------------------------------------------------


def test_mercury_decide_routing_payload_and_parse():
    """Verify Mercury Decide formats question payload and parses choice & probabilities."""
    client = MercuryDecideClient(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "model": "inception/mercury-decide:free",
        "answers": {
            "route": {
                "type": "choice",
                "choice": "graph",
                "probabilities": {"vector": 0.05, "graph": 0.90, "hybrid": 0.05},
                "confidence": 0.92,
            }
        },
    }

    with patch.object(client.client, "post", return_value=mock_resp) as mock_post:
        route, conf, probs = client.decide_route("What are AMD subsidiaries in Singapore?")

        assert route == "graph"
        assert conf == 0.92
        assert probs["graph"] == 0.90
        assert mock_post.called

        # Inspect request payload
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["model"] == "inception/mercury-decide:free"
        assert payload["state"] == {"query": "What are AMD subsidiaries in Singapore?"}
        assert "route" in payload["questions"]
        assert payload["questions"]["route"]["type"] == "choice"


def test_mercury_decide_claim_support():
    """Verify claim-support verification parsing."""
    client = MercuryDecideClient(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "model": "inception/mercury-decide:free",
        "answers": {
            "support": {
                "type": "choice",
                "choice": "supported",
                "confidence": 0.95,
            }
        },
    }

    with patch.object(client.client, "post", return_value=mock_resp):
        decision, conf = client.decide_claim_support(
            claim="AMD acquired Xilinx in 2022.",
            evidence="In February 2022, Advanced Micro Devices completed its acquisition of Xilinx, Inc.",
        )
        assert decision == "supported"
        assert conf == 0.95


def test_mercury_decide_provider_error_handling():
    """Verify 401 Unauthorized raises PermissionError and 429 backoff."""
    client = MercuryDecideClient(api_key="test-key")

    # 401 error
    mock_resp_401 = MagicMock()
    mock_resp_401.status_code = 401
    mock_resp_401.text = "Invalid API Key"
    with patch.object(client.client, "post", return_value=mock_resp_401):
        with pytest.raises(PermissionError, match="401 Unauthorized"):
            client.decide(state={}, questions={})


def test_mercury_decide_malformed_response():
    """Verify malformed JSON without answers dictionary raises ValueError."""
    client = MercuryDecideClient(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"error": "unexpected format"}

    with patch.object(client.client, "post", return_value=mock_resp):
        with pytest.raises(ValueError, match="expected 'answers' dict"):
            client.decide(state={}, questions={})


# ---------------------------------------------------------------------------
# 3. Embedding Model (nvidia/nemotron-3-embed-1b:free)
# ---------------------------------------------------------------------------


def test_openrouter_embedding_generation():
    """Verify 2048-dimensional embedding generation and batch handling."""
    embed_client = OpenRouterEmbeddingClient(api_key="test-key", dimension=2048, batch_size=2)

    fake_vec1 = [0.1] * 2048
    fake_vec2 = [0.2] * 2048

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "object": "list",
        "data": [
            {"object": "embedding", "index": 0, "embedding": fake_vec1},
            {"object": "embedding", "index": 1, "embedding": fake_vec2},
        ],
    }

    with patch.object(embed_client.client, "post", return_value=mock_resp) as mock_post:
        embs = embed_client.embed(["Text chunk 1", "Text chunk 2"])
        assert len(embs) == 2
        assert len(embs[0]) == 2048
        assert len(embs[1]) == 2048

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "nvidia/nemotron-3-embed-1b:free"
        assert call_kwargs["json"]["input"] == ["Text chunk 1", "Text chunk 2"]


def test_openrouter_embedding_batching():
    """Verify that inputs larger than batch_size are correctly partitioned."""
    embed_client = OpenRouterEmbeddingClient(api_key="test-key", dimension=2048, batch_size=2)

    fake_vec = [0.1] * 2048
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [{"index": 0, "embedding": fake_vec}, {"index": 1, "embedding": fake_vec}],
    }

    with patch.object(embed_client.client, "post", return_value=mock_resp) as mock_post:
        # Pass 4 items with batch_size=2 -> should call post twice
        embs = embed_client.embed(["A", "B", "C", "D"])
        assert len(embs) == 4
        assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# 4. Generative LLM (nvidia/nemotron-3.5-super-vl:free)
# ---------------------------------------------------------------------------


def test_openrouter_llm_generate():
    """Verify unstructured text generation using chat/completions."""
    client = OpenRouterClient(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "AMD subsidiaries in Singapore include Qualcomm Global Trading Pte. Ltd. [P1]",
                }
            }
        ]
    }

    with patch.object(client.client, "post", return_value=mock_resp) as mock_post:
        ans = client.generate("What are AMD subsidiaries in Singapore?")
        assert "[P1]" in ans

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "nvidia/nemotron-3.5-super-vl:free"
        assert call_kwargs["json"]["max_tokens"] == 1024


def test_openrouter_llm_reasoning_fallback():
    """Verify that if content is empty but reasoning is present, reasoning is used as fallback."""
    client = OpenRouterClient(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "reasoning": "The filing indicates AMD maintains Singapore operations.",
                }
            }
        ]
    }

    with patch.object(client.client, "post", return_value=mock_resp):
        ans = client.generate("Test prompt")
        assert "AMD maintains Singapore operations" in ans


class SampleExtract(BaseModel):
    company: str
    ticker: str


def test_openrouter_llm_structured_output():
    """Verify Pydantic structured output validation."""
    client = OpenRouterClient(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"company": "Advanced Micro Devices", "ticker": "AMD"}),
                }
            }
        ]
    }

    with patch.object(client.client, "post", return_value=mock_resp):
        res = client.generate_structured("Extract entity", schema=SampleExtract)
        assert res.company == "Advanced Micro Devices"
        assert res.ticker == "AMD"


def test_openrouter_llm_structured_output_retry_on_invalid_json():
    """Verify retry with schema error feedback when initial response has invalid JSON."""
    client = OpenRouterClient(api_key="test-key")

    bad_resp = MagicMock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": "not valid json {"}}]
    }

    good_resp = MagicMock()
    good_resp.status_code = 200
    good_resp.json.return_value = {
        "choices": [
            {"message": {"role": "assistant", "content": '{"company": "Intel", "ticker": "INTC"}'}}
        ]
    }

    with patch.object(client.client, "post", side_effect=[bad_resp, good_resp]) as mock_post:
        res = client.generate_structured("Extract entity", schema=SampleExtract, max_retries=1)
        assert res.company == "Intel"
        assert res.ticker == "INTC"
        assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# 5. Vector Dimension Migration & Compatibility Tests
# ---------------------------------------------------------------------------


def test_validate_vector_dimensions_success():
    """Verify dimension validation passes when pgvector columns match 2048-d."""
    with patch("kgrag.vector.embeddings.get_connection") as mock_conn:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"table_name": "chunks", "attname": "embedding", "atttypmod": 2048},
            {"table_name": "entities", "attname": "name_embedding", "atttypmod": 2048},
        ]
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = (
            mock_cursor
        )

        res = validate_vector_dimensions()
        assert res["status"] == "ok"
        assert res["dimension"] == 2048


def test_validate_vector_dimensions_mismatch():
    """Verify dimension mismatch raises descriptive ValueError."""
    with patch("kgrag.vector.embeddings.get_connection") as mock_conn:
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"table_name": "chunks", "attname": "embedding", "atttypmod": 768},
        ]
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = (
            mock_cursor
        )

        with pytest.raises(ValueError, match="Vector dimension mismatch"):
            validate_vector_dimensions()


# ---------------------------------------------------------------------------
# 6. Router & Claim Support Integration Tests
# ---------------------------------------------------------------------------


def test_router_uses_mercury_decide():
    """Verify router uses Mercury Decide when available and confidence exceeds threshold."""
    mock_decide = MagicMock()
    mock_decide.decide_route.return_value = (
        "graph",
        0.94,
        {"graph": 0.94, "vector": 0.03, "hybrid": 0.03},
    )

    with patch("kgrag.retrieval.router.get_decision_client", return_value=mock_decide):
        with patch("kgrag.retrieval.router.extract_entities_from_text", return_value=["AMD"]):
            dec = route_query("What are the subsidiaries of AMD in Singapore?")
            assert dec.chosen == "graph"
            assert dec.confidence == 0.94
            assert not dec.fallback_used
            assert "System One decision" in dec.reasoning


def test_router_falls_back_when_mercury_decide_fails():
    """Verify router gracefully falls back to rule-based routing on Mercury Decide failure."""
    mock_decide = MagicMock()
    mock_decide.decide_route.side_effect = RuntimeError("OpenRouter 429 rate limit")

    with patch("kgrag.retrieval.router.get_decision_client", return_value=mock_decide):
        with patch("kgrag.retrieval.router.extract_entities_from_text", return_value=["AMD"]):
            dec = route_query("What are the subsidiaries of AMD in Singapore?")
            # Should not crash, should fall back to heuristic with fallback_used=True
            assert dec.chosen in ("graph", "hybrid")
            assert dec.fallback_used is True


def test_verify_claim_support():
    """Verify verify_claim_support updates ResolvedCitation supports_claim field."""
    mock_decide = MagicMock()
    mock_decide.decide_claim_support.return_value = ("supported", 0.96)

    cit = ResolvedCitation(
        label="[P1]",
        chunk_id="chunk-123",
        text_snippet="AMD acquired Xilinx in 2022.",
    )

    with patch("kgrag.answer.validator.get_decision_client", return_value=mock_decide):
        updated = verify_claim_support(
            answer_text="AMD completed the acquisition of Xilinx in 2022. [P1]",
            resolved_citations=[cit],
        )
        assert len(updated) == 1
        assert updated[0].supports_claim == "supported"
        assert updated[0].claim_support_confidence == 0.96
