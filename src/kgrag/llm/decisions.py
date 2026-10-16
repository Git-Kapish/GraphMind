"""System One Decision Client abstraction supporting OpenRouter Decisions API (PRD §7.3, §8).

Uses `inception/mercury-decide:free` via OpenRouter's `/api/alpha/decisions` endpoint for
bounded, calibrated probabilistic decisions (e.g. query routing and claim-support verification).
"""

import logging
import os
import time
from typing import Any, Literal, Protocol

import httpx

from kgrag.config import get_settings

logger = logging.getLogger(__name__)


class DecisionClient(Protocol):
    """Protocol for System One structured decision models."""

    def decide(
        self, state: dict[str, Any], questions: dict[str, Any], timeout: float | None = None
    ) -> dict[str, Any]:
        """Execute a structured decision query returning answers with calibrated probabilities."""
        ...

    def decide_route(
        self, question: str
    ) -> tuple[Literal["vector", "graph", "hybrid"], float, dict[str, float]]:
        """Bounded routing decision classifying query intent into vector, graph, or hybrid."""
        ...

    def decide_claim_support(
        self, claim: str, evidence: str
    ) -> tuple[Literal["supported", "unsupported"], float]:
        """Bounded claim-support decision determining if evidence substantiates a claim."""
        ...

    def check_health(self) -> dict[str, Any]:
        """Check reachability and credentials for the decision model."""
        ...


class MercuryDecideClient:
    """Inception Labs Mercury Decide implementation via OpenRouter Decisions API."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ):
        settings = get_settings()
        self.api_key = (
            api_key or settings.system_one.api_key or os.getenv("OPENROUTER_API_KEY", "")
        ).strip()
        self.endpoint = (endpoint or settings.system_one.endpoint).rstrip("/")
        self.model = model or settings.system_one.model
        self.timeout_seconds = timeout_seconds or settings.system_one.timeout_seconds

        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        self.client = httpx.Client(timeout=self.timeout_seconds, limits=limits)

    def close(self) -> None:
        """Close underlying HTTP client session."""
        if hasattr(self, "client") and self.client is not None:
            self.client.close()

    def __enter__(self) -> "MercuryDecideClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is missing or empty. "
                "Configure OPENROUTER_API_KEY in your environment or .env file."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Git-Kapish/GraphMind",
            "X-Title": "GraphMind System One Decision",
        }

    def check_health(self) -> dict[str, Any]:
        """Verify reachability and credential status for Mercury Decide."""
        if not self.api_key:
            return {
                "status": "unconfigured",
                "model": self.model,
                "error": "OPENROUTER_API_KEY is not configured.",
            }
        if self.api_key.startswith("mock"):
            return {
                "status": "healthy",
                "endpoint": self.endpoint,
                "model": self.model,
                "provider": "Inception Labs (OpenRouter Decisions Mock)",
            }
        try:
            # Send a minimal dry-run decision query to verify reachability
            res = self.decide(
                state={"test": True},
                questions={
                    "ping": {
                        "type": "noul",
                        "instructions": "Is this a health check ping?",
                    }
                },
                timeout=10.0,
            )
            return {
                "status": "healthy" if "ping" in res else "degraded",
                "endpoint": self.endpoint,
                "model": self.model,
                "provider": "Inception Labs (OpenRouter Decisions)",
            }
        except Exception as e:
            logger.warning("Mercury Decide health check failed: %s", e)
            return {
                "status": "unhealthy",
                "endpoint": self.endpoint,
                "model": self.model,
                "error": str(e),
            }

    def decide(
        self, state: dict[str, Any], questions: dict[str, Any], timeout: float | None = None
    ) -> dict[str, Any]:
        """Send decision request to OpenRouter Decisions API and parse answers."""
        if self.api_key.startswith("mock"):
            mock_answers = {}
            for q_name, q_spec in questions.items():
                if q_spec.get("type") == "choice":
                    criteria = q_spec.get("criteria", {})
                    choices = list(criteria.keys()) if criteria else ["vector", "graph", "hybrid"]
                    choice = choices[0] if choices else "vector"
                    mock_answers[q_name] = {
                        "type": "choice",
                        "choice": choice,
                        "confidence": 0.95,
                        "probabilities": {
                            c: (0.95 if c == choice else 0.05 / max(1, len(choices) - 1))
                            for c in choices
                        },
                    }
                else:
                    mock_answers[q_name] = {
                        "type": "noul",
                        "value": "supported",
                        "confidence": 0.90,
                    }
            return mock_answers

        headers = self._get_headers()
        payload = {
            "model": self.model,
            "state": state,
            "questions": questions,
        }

        max_retries = 2
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                resp = self.client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=timeout or self.timeout_seconds,
                )
                if resp.status_code == 401:
                    raise PermissionError(
                        f"OpenRouter authentication failed (401 Unauthorized): {resp.text}"
                    )
                if resp.status_code == 429:
                    last_error = httpx.HTTPStatusError(
                        f"429 Rate Limit from OpenRouter: {resp.text}",
                        request=resp.request,
                        response=resp,
                    )
                    wait_time = 1.0 * (2**attempt)
                    try:
                        err_data = resp.json().get("error", {})
                        if "metadata" in err_data and "recheck_after" in err_data["metadata"]:
                            wait_time = float(err_data["metadata"]["recheck_after"])
                    except Exception:
                        pass
                    reset_header = resp.headers.get("X-RateLimit-Reset")
                    if reset_header:
                        try:
                            reset_epoch = float(reset_header)
                            diff = reset_epoch - time.time()
                            if 0 < diff < 60:
                                wait_time = max(wait_time, diff + 0.5)
                        except Exception:
                            pass
                    logger.warning(
                        "OpenRouter Decisions API rate-limited (429); backing off %.1fs (attempt %d/%d)...",
                        wait_time,
                        attempt + 1,
                        max_retries + 1,
                    )
                    time.sleep(wait_time)
                    continue

                resp.raise_for_status()
                data = resp.json()
                answers = data.get("answers")
                if answers is None or not isinstance(answers, dict):
                    raise ValueError(
                        f"Malformed response from OpenRouter Decisions API: expected 'answers' dict, got: {data}"
                    )
                return answers
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_error = e
                logger.warning(
                    "Attempt %d/%d to Decisions API (%s) failed: %s",
                    attempt + 1,
                    max_retries + 1,
                    self.endpoint,
                    e,
                )
                if attempt < max_retries:
                    time.sleep(0.5 * (attempt + 1))

        raise RuntimeError(
            f"OpenRouter Decisions API failed after {max_retries + 1} attempts. Last error: {last_error}"
        ) from last_error

    def decide_route(
        self, question: str
    ) -> tuple[Literal["vector", "graph", "hybrid"], float, dict[str, float]]:
        """Bounded classification of user query into 'vector', 'graph', or 'hybrid'."""
        state = {"query": question}
        questions = {
            "route": {
                "type": "choice",
                "instructions": (
                    "Determine whether to route this financial SEC 10-K query to vector search, "
                    "graph search, or hybrid search based on structural vs narrative needs."
                ),
                "criteria": {
                    "vector": (
                        "Unstructured narrative disclosures, general business descriptions, MD&A trends, "
                        "accounting policies, risk factor explanations, or high-level macroeconomic topics."
                    ),
                    "graph": (
                        "Direct entity relationships, organizational structure, subsidiaries, Exhibit 21 listings, "
                        "executive officers, board directors, supply chain partners, or multi-hop connection paths."
                    ),
                    "hybrid": (
                        "Complex relational inquiries that also require contextual narrative evidence from the text "
                        "of SEC filings, combining structural entities with textual elaboration."
                    ),
                },
            }
        }

        answers = self.decide(state, questions)
        route_answer = answers.get("route")
        if not route_answer or "choice" not in route_answer:
            raise ValueError(f"Decision response missing 'route' choice: {answers}")

        choice = route_answer["choice"]
        if choice not in ("vector", "graph", "hybrid"):
            choice = "hybrid"

        confidence = float(route_answer.get("confidence", 0.85))
        probabilities = route_answer.get("probabilities", {choice: confidence})
        prob_dict = {k: float(v) for k, v in probabilities.items()}

        return choice, confidence, prob_dict

    def decide_claim_support(
        self, claim: str, evidence: str
    ) -> tuple[Literal["supported", "unsupported"], float]:
        """Bounded evaluation verifying whether retrieved passage evidence substantiates a claim."""
        state = {"claim": claim, "evidence": evidence}
        questions = {
            "support": {
                "type": "choice",
                "instructions": (
                    "Determine whether the claim made in the financial answer is explicitly substantiated "
                    "by the retrieved SEC filing evidence quote."
                ),
                "criteria": {
                    "supported": (
                        "The factual statements, numbers, names, or relationships stated in the claim "
                        "are directly supported by the excerpt."
                    ),
                    "unsupported": (
                        "The claim makes assertions, numbers, or conclusions not verified or contradicted "
                        "by the excerpt."
                    ),
                },
            }
        }

        answers = self.decide(state, questions)
        support_answer = answers.get("support")
        if not support_answer or "choice" not in support_answer:
            return "unsupported", 0.5

        choice = support_answer["choice"]
        valid_choice = "supported" if choice == "supported" else "unsupported"
        confidence = float(support_answer.get("confidence", 0.85))

        return valid_choice, confidence


_default_decision_client: DecisionClient | None = None


def get_decision_client() -> DecisionClient:
    """Get or create singleton System One decision client."""
    global _default_decision_client
    if _default_decision_client is None:
        _default_decision_client = MercuryDecideClient()
    return _default_decision_client


def close_decision_client() -> None:
    """Safely shut down the singleton decision client session."""
    global _default_decision_client
    if _default_decision_client is not None:
        if hasattr(_default_decision_client, "close"):
            _default_decision_client.close()
        _default_decision_client = None
