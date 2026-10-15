"""Local LLM Client abstraction supporting Ollama and structured JSON generation (PRD §6, §18)."""

import json
import logging
import time
from typing import Any, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from kgrag.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    """Protocol for LLM interactions (local-first with $0 spend)."""

    def generate(
        self, prompt: str, temperature: float | None = None, timeout: float | None = None
    ) -> str:
        """Generate unstructured text from prompt."""
        ...

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        temperature: float | None = None,
        max_retries: int | None = None,
    ) -> T:
        """Generate structured Pydantic object with validation and retry feedback."""
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for input texts."""
        ...

    def check_health(self) -> dict[str, Any]:
        """Check LLM service reachability and model availability."""
        ...


def _pydantic_to_template_dict(schema: type[BaseModel]) -> dict[str, Any]:
    """Generate a clean example JSON template matching Pydantic fields."""
    template = {}
    for name, field in getattr(schema, "model_fields", {}).items():
        annotation = field.annotation
        if annotation is str:
            template[name] = "string"
        elif annotation in (int, float):
            template[name] = 0.0
        elif annotation is bool:
            template[name] = True
        elif getattr(annotation, "__origin__", None) is list or getattr(annotation, "__name__", "") == "list":
            template[name] = []
        elif getattr(annotation, "__origin__", None) is dict or getattr(annotation, "__name__", "") == "dict":
            template[name] = {}
        else:
            template[name] = "string"
    return template


class OllamaClient:
    """Ollama implementation of LLMClient protocol."""

    def __init__(
        self,
        endpoint: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
        timeout_seconds: float | None = None,
    ):
        settings = get_settings()
        self.endpoint = (endpoint or settings.llm.endpoint).rstrip("/")
        self.model = model or settings.llm.model
        self.embedding_model = embedding_model or settings.embedding.model
        self.timeout_seconds = timeout_seconds or settings.llm.timeout_seconds
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        self.client = httpx.Client(timeout=self.timeout_seconds, limits=limits)

    def close(self) -> None:
        """Close underlying HTTP client session."""
        if hasattr(self, "client") and self.client is not None:
            self.client.close()

    def __enter__(self) -> "OllamaClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def check_health(self) -> dict[str, Any]:
        """Verify Ollama reachability and list available models."""
        url = f"{self.endpoint}/api/tags"
        try:
            resp = self.client.get(url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                model_present = any(self.model in m for m in models)
                return {
                    "status": "healthy",
                    "endpoint": self.endpoint,
                    "target_model": self.model,
                    "model_available": model_present,
                    "available_models": models,
                }
            return {
                "status": "unhealthy",
                "status_code": resp.status_code,
                "error": resp.text,
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "endpoint": self.endpoint,
                "error": str(e),
            }

    def generate(
        self, prompt: str, temperature: float | None = None, timeout: float | None = None
    ) -> str:
        url = f"{self.endpoint}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
                if temperature is not None
                else get_settings().llm.temperature,
            },
        }
        resp = self.client.post(url, json=payload, timeout=timeout or self.timeout_seconds)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        temperature: float | None = None,
        max_retries: int | None = None,
    ) -> T:
        """Request JSON format, validate with Pydantic, and retry on validation errors."""
        url = f"{self.endpoint}/api/generate"
        retries = max_retries if max_retries is not None else get_settings().llm.max_retries
        current_prompt = prompt
        schema_json_str = json.dumps(schema.model_json_schema(), indent=2)

        if getattr(schema, "__name__", "") == "ExtractionResult":
            format_instruction = (
                "{\n"
                '  "chunk_id": "string",\n'
                '  "relations": [\n'
                "    {\n"
                '      "head_name": "string",\n'
                '      "head_type": "Company|Person|Product|Technology|Market|Location|Regulation",\n'
                '      "relation": "RELATION_TYPE",\n'
                '      "tail_name": "string",\n'
                '      "tail_type": "Company|Person|Product|Technology|Market|Location|Regulation",\n'
                '      "evidence_quote": "verbatim sentence from text",\n'
                '      "confidence": 0.95\n'
                "    }\n"
                "  ]\n"
                "}\n"
                'If no explicit relationships exist in the text, return: {"chunk_id": "...", "relations": []}.'
            )
        else:
            template = _pydantic_to_template_dict(schema)
            format_instruction = json.dumps(template, indent=2) if template else schema_json_str

        for attempt in range(retries + 1):
            enhanced_prompt = (
                f"{current_prompt}\n\n"
                f"OUTPUT FORMAT REQUIREMENT:\n"
                f"Respond ONLY with a valid JSON object matching this structure with the actual values filled in:\n"
                f"{format_instruction}\n"
                f"No markdown backticks, no comments, no explanation outside the JSON."
            )
            payload = {
                "model": self.model,
                "prompt": enhanced_prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": temperature if temperature is not None else 0.0,
                },
            }

            start_t = time.perf_counter()
            resp = self.client.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)

            raw_text = resp.json().get("response", "").strip()
            try:
                data = json.loads(raw_text)
                parsed = schema.model_validate(data)
                logger.debug("Structured output successfully parsed in %d ms", elapsed_ms)
                return parsed
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(
                    "Attempt %d/%d structured parsing failed: %s", attempt + 1, retries + 1, e
                )
                if attempt == retries:
                    raise ValueError(
                        f"Failed to generate valid structured output after {retries + 1} attempts. "
                        f"Last error: {e}. Raw output: {raw_text[:500]}"
                    ) from e
                # Formulate feedback prompt for retry
                current_prompt = (
                    f"{prompt}\n\n"
                    f"Previous attempt produced invalid JSON or violated schema constraints:\n"
                    f"Error: {e}\n"
                    f"Invalid output was:\n{raw_text}\n"
                    f"Please correct the error and output valid JSON conforming strictly to the schema."
                )

        raise RuntimeError("Unreachable state in generate_structured")

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using Ollama embedding endpoint."""
        url = f"{self.endpoint}/api/embed"
        # Newer Ollama supports /api/embed with multi-text input
        try:
            payload = {
                "model": self.embedding_model,
                "input": texts,
            }
            resp = self.client.post(url, json=payload, timeout=self.timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("embeddings", [])
        except Exception as e:
            logger.debug("Ollama /api/embed failed, falling back to /api/embeddings: %s", e)

        # Fallback to single-item /api/embeddings
        fallback_url = f"{self.endpoint}/api/embeddings"
        embeddings = []
        for text in texts:
            payload = {"model": self.embedding_model, "prompt": text}
            resp = self.client.post(fallback_url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            embeddings.append(resp.json().get("embedding", []))
        return embeddings


_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create singleton LLM client."""
    global _default_client
    if _default_client is None:
        _default_client = OllamaClient()
    return _default_client


def close_llm_client() -> None:
    """Safely shut down the singleton LLM client session."""
    global _default_client
    if _default_client is not None:
        if hasattr(_default_client, "close"):
            _default_client.close()
        _default_client = None

