"""Smoke test for local LLM structured generation (M0 acceptance check)."""

import os

import pytest
from pydantic import BaseModel

from kgrag.llm.client import get_llm_client


class SmokeOutput(BaseModel):
    name: str
    category: str
    confidence: float


def is_live_llm_configured() -> bool:
    key = os.getenv("OPENROUTER_API_KEY", "")
    return bool(key and not key.startswith("mock") and len(key) > 10)


@pytest.mark.skipif(not is_live_llm_configured(), reason="Requires live LLM credentials")
def test_ollama_health():
    client = get_llm_client()
    health = client.check_health()
    assert health["status"] == "healthy"
    assert health["model_available"] is True


@pytest.mark.skipif(not is_live_llm_configured(), reason="Requires live LLM credentials")
def test_ollama_structured_smoke():
    client = get_llm_client()
    prompt = (
        "Classify the following entity: 'NVIDIA Corporation'. "
        "Return the entity name, its primary industry category, and your confidence score between 0 and 1."
    )
    result = client.generate_structured(prompt, SmokeOutput)
    assert isinstance(result, SmokeOutput)
    assert "nvidia" in result.name.lower()
    assert len(result.category) > 0
    assert 0.0 <= result.confidence <= 1.0
