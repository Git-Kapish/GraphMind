"""Integration tests for FastAPI health endpoint (PRD §8)."""

import httpx

from kgrag.api.app import app


async def test_health_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "postgres" in data["components"]
        assert "neo4j" in data["components"]
        assert "llm" in data["components"]

        # Invariant check: secrets MUST NEVER be leaked in health check (§8)
        content_str = response.text
        assert "password" not in content_str.lower()
        assert "secret" not in content_str.lower()
        assert "eVCj08KwjoyjuTzL2FNz37mKEUonh5lw" not in content_str
        assert "9u9BNwZttIrUDOtA9OhRQRDC00GpLN6x" not in content_str
