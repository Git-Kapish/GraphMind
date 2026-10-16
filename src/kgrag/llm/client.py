"""Local LLM Client abstraction supporting Ollama and structured JSON generation (PRD §6, §18)."""

import json
import logging
import os
import re
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
        elif (
            getattr(annotation, "__origin__", None) is list
            or getattr(annotation, "__name__", "") == "list"
        ):
            template[name] = []
        elif (
            getattr(annotation, "__origin__", None) is dict
            or getattr(annotation, "__name__", "") == "dict"
        ):
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
                "num_predict": 256,
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


class OpenRouterEmbeddingClient:
    """OpenRouter implementation for dense vector embeddings using nvidia/nemotron-3-embed-1b:free."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        dimension: int | None = None,
        batch_size: int | None = None,
        timeout_seconds: float | None = None,
    ):
        settings = get_settings()
        self.api_key = (
            api_key or settings.embedding.api_key or os.getenv("OPENROUTER_API_KEY", "")
        ).strip()
        self.endpoint = (endpoint or settings.embedding.endpoint).rstrip("/")
        self.model = model or settings.embedding.model
        self.dimension = dimension or settings.embedding.dimension
        self.batch_size = batch_size or settings.embedding.batch_size
        self.timeout_seconds = timeout_seconds or 60.0

        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        self.client = httpx.Client(timeout=self.timeout_seconds, limits=limits)
        self._cache: dict[str, list[float]] = {}

    def close(self) -> None:
        if hasattr(self, "client") and self.client is not None:
            self.client.close()

    def __enter__(self) -> "OpenRouterEmbeddingClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured. "
                "Please configure OPENROUTER_API_KEY in your environment or .env file."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Git-Kapish/GraphMind",
            "X-Title": "GraphMind Embeddings",
        }

    def check_health(self) -> dict[str, Any]:
        """Check reachability and API key for OpenRouter embeddings."""
        if not self.api_key:
            return {"status": "unconfigured", "error": "OPENROUTER_API_KEY not configured"}
        try:
            embs = self.embed(["test reachability"])
            dim = len(embs[0]) if embs else 0
            return {
                "status": "healthy" if dim > 0 else "degraded",
                "model": self.model,
                "dimension": dim,
                "endpoint": self.endpoint,
            }
        except Exception as e:
            return {"status": "unhealthy", "model": self.model, "error": str(e)}

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate 2048-d vector embeddings using OpenRouter /embeddings endpoint with in-memory caching."""
        if not texts:
            return []

        # 1. Check in-memory cache for existing embeddings
        needed_indices = []
        uncached_texts = []
        results: list[list[float] | None] = [None] * len(texts)

        for idx, text in enumerate(texts):
            clean_text = text.strip() if text and text.strip() else "unknown"
            if clean_text in self._cache:
                results[idx] = self._cache[clean_text]
            else:
                needed_indices.append(idx)
                uncached_texts.append(clean_text)

        if not uncached_texts:
            return [r for r in results if r is not None]

        headers = self._get_headers()
        url = f"{self.endpoint}/embeddings"

        for i in range(0, len(uncached_texts), self.batch_size):
            batch = uncached_texts[i : i + self.batch_size]
            batch_orig_indices = needed_indices[i : i + self.batch_size]
            payload = {
                "model": self.model,
                "input": batch,
            }

            max_retries = 4
            last_err: Exception | None = None
            success = False

            for attempt in range(max_retries + 1):
                try:
                    resp = self.client.post(
                        url, headers=headers, json=payload, timeout=self.timeout_seconds
                    )
                    if resp.status_code == 401:
                        raise PermissionError(
                            f"OpenRouter authentication failed (401): {resp.text}"
                        )
                    if resp.status_code == 400:
                        raise ValueError(f"OpenRouter embeddings 400 Bad Request: {resp.text}")
                    if resp.status_code == 429:
                        last_err = httpx.HTTPStatusError(
                            f"429 Rate Limit from OpenRouter: {resp.text}",
                            request=resp.request,
                            response=resp,
                        )
                        # Extract smart wait time from headers or JSON body
                        wait_t = 2.0 * (2**attempt)
                        try:
                            err_data = resp.json().get("error", {})
                            meta_headers = err_data.get("metadata", {}).get("headers", {})
                            reset_raw = meta_headers.get("X-RateLimit-Reset") or resp.headers.get(
                                "X-RateLimit-Reset"
                            )
                            if reset_raw:
                                reset_sec = float(reset_raw)
                                if reset_sec > 1e11:  # ms to sec
                                    reset_sec /= 1000.0
                                wait_t = max(1.0, min(15.0, reset_sec - time.time()))
                        except Exception:
                            pass
                        logger.warning(
                            "OpenRouter embeddings 429 rate limit; sleeping %.1fs...", wait_t
                        )
                        time.sleep(wait_t)
                        continue
                    resp.raise_for_status()
                    data = resp.json().get("data", [])
                    sorted_data = sorted(data, key=lambda x: x.get("index", 0))
                    for item, text_key, target_idx in zip(sorted_data, batch, batch_orig_indices):
                        emb = item.get("embedding", [])
                        if len(emb) != self.dimension:
                            logger.warning(
                                "Embedding dimension mismatch: expected %d, got %d",
                                self.dimension,
                                len(emb),
                            )
                        self._cache[text_key] = emb
                        results[target_idx] = emb
                    success = True
                    break
                except (httpx.RequestError, httpx.HTTPStatusError) as e:
                    last_err = e
                    logger.warning(
                        "Attempt %d/%d for embeddings failed: %s", attempt + 1, max_retries + 1, e
                    )
                    if attempt < max_retries:
                        time.sleep(1.0 * (attempt + 1))

            if not success:
                raise RuntimeError(
                    f"Failed to generate embeddings via OpenRouter after {max_retries + 1} attempts. Last error: {last_err}"
                ) from last_err

        return [r for r in results if r is not None]


class OpenRouterClient:
    """OpenRouter implementation of LLMClient protocol using nvidia/nemotron-3.5-super-vl:free."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        embedding_client: OpenRouterEmbeddingClient | None = None,
    ):
        settings = get_settings()
        self.api_key = (
            api_key or settings.llm.api_key or os.getenv("OPENROUTER_API_KEY", "")
        ).strip()
        self.endpoint = (endpoint or settings.llm.endpoint).rstrip("/")
        self.model = model or settings.llm.model
        self.timeout_seconds = timeout_seconds or settings.llm.timeout_seconds
        self.temperature = settings.llm.temperature
        self.embedding_client = embedding_client or OpenRouterEmbeddingClient(api_key=self.api_key)

        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        self.client = httpx.Client(timeout=self.timeout_seconds, limits=limits)

    def close(self) -> None:
        if hasattr(self, "client") and self.client is not None:
            self.client.close()
        if hasattr(self, "embedding_client") and self.embedding_client is not None:
            self.embedding_client.close()

    def __enter__(self) -> "OpenRouterClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not configured. "
                "Please configure OPENROUTER_API_KEY in your environment or .env file."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Git-Kapish/GraphMind",
            "X-Title": "GraphMind LLM",
        }

    def check_health(self) -> dict[str, Any]:
        """Check OpenRouter reachability and credentials."""
        if not self.api_key:
            return {
                "status": "unconfigured",
                "model": self.model,
                "error": "OPENROUTER_API_KEY is not configured.",
            }
        try:
            resp = self.client.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers=self._get_headers(),
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return {
                    "status": "healthy",
                    "provider": "OpenRouter",
                    "target_model": self.model,
                    "model_available": True,
                    "label": data.get("label", "valid"),
                    "limit": data.get("limit"),
                }
            return {
                "status": "unhealthy",
                "status_code": resp.status_code,
                "error": resp.text,
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e),
            }

    def generate(
        self, prompt: str, temperature: float | None = None, timeout: float | None = None
    ) -> str:
        """Generate unstructured text from prompt using OpenRouter /chat/completions."""
        url = f"{self.endpoint}/chat/completions"
        headers = self._get_headers()
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": 1024,
        }

        resp = self.client.post(
            url, headers=headers, json=payload, timeout=timeout or self.timeout_seconds
        )
        if resp.status_code == 401:
            raise PermissionError(f"OpenRouter authentication failed (401): {resp.text}")
        resp.raise_for_status()

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return ""

        msg = choices[0].get("message", {})
        content = msg.get("content") or ""
        if not content and "reasoning" in msg:
            logger.warning("Model produced reasoning without content; using reasoning fallback")
            content = msg.get("reasoning", "")

        return content.strip()

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        temperature: float | None = None,
        max_retries: int | None = None,
    ) -> T:
        """Generate structured Pydantic object using response_format: {type: json_object}."""
        url = f"{self.endpoint}/chat/completions"
        headers = self._get_headers()
        retries = max_retries if max_retries is not None else get_settings().llm.max_retries
        current_prompt = prompt

        template = _pydantic_to_template_dict(schema)
        format_instruction = (
            json.dumps(template, indent=2)
            if template
            else json.dumps(schema.model_json_schema(), indent=2)
        )

        for attempt in range(retries + 1):
            enhanced_prompt = (
                f"{current_prompt}\n\n"
                f"OUTPUT FORMAT REQUIREMENT:\n"
                f"Respond ONLY with a valid JSON object strictly matching this schema with actual values:\n"
                f"{format_instruction}\n"
                f"Do NOT include markdown fences, comments, or explanation outside the JSON."
            )
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a precise financial data extraction system. Output strictly valid JSON.",
                    },
                    {"role": "user", "content": enhanced_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": temperature if temperature is not None else 0.0,
                "max_tokens": 1024,
            }

            start_t = time.perf_counter()
            resp = self.client.post(
                url, headers=headers, json=payload, timeout=self.timeout_seconds
            )
            if resp.status_code == 401:
                raise PermissionError(f"OpenRouter authentication failed (401): {resp.text}")
            resp.raise_for_status()
            elapsed_ms = int((time.perf_counter() - start_t) * 1000)

            data = resp.json()
            choices = data.get("choices", [])
            raw_text = choices[0]["message"].get("content", "").strip() if choices else ""

            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                raw_text = raw_text.strip()

            try:
                parsed_json = json.loads(raw_text)
                validated = schema.model_validate(parsed_json)
                logger.debug("Structured output successfully parsed in %d ms", elapsed_ms)
                return validated
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(
                    "Attempt %d/%d structured parsing failed: %s", attempt + 1, retries + 1, e
                )
                if attempt == retries:
                    raise ValueError(
                        f"Failed to generate valid structured output after {retries + 1} attempts. "
                        f"Last error: {e}. Raw output: {raw_text[:500]}"
                    ) from e

                current_prompt = (
                    f"{prompt}\n\n"
                    f"Previous attempt produced invalid JSON or violated schema constraints:\n"
                    f"Error: {e}\n"
                    f"Invalid output was:\n{raw_text}\n"
                    f"Please correct the error and output valid JSON conforming strictly to the schema."
                )

        raise RuntimeError("Unreachable state in generate_structured")

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Delegate embedding generation to OpenRouterEmbeddingClient."""
        return self.embedding_client.embed(texts)


_default_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create singleton LLM client based on configured runtime."""
    global _default_client
    settings = get_settings()
    if _default_client is None:
        if settings.llm.runtime == "openrouter":
            _default_client = OpenRouterClient()
        else:
            _default_client = OllamaClient()
    return _default_client


def close_llm_client() -> None:
    """Safely shut down the singleton LLM client session."""
    global _default_client
    if _default_client is not None:
        if hasattr(_default_client, "close"):
            _default_client.close()
        _default_client = None
