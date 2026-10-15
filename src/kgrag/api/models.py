"""API Request and Response Models (PRD §8)."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded", "unhealthy"]
    timestamp: str
    version: str
    components: dict[str, ComponentHealth]


class CitationItem(BaseModel):
    label: str  # e.g., "P1", "G1"
    chunk_id: str
    doc: str
    section: str
    snippet: str
    supports_claim: Literal["supported", "unsupported", "unknown"] = "unknown"


class RouteInfo(BaseModel):
    chosen: Literal["vector", "graph", "hybrid"]
    confidence: float
    fallback_used: bool = False


class ValidationResult(BaseModel):
    citation_resolution_passed: bool
    claim_support_status: str = "not_evaluated"
    attempts: int = 1


class LatencyBreakdown(BaseModel):
    route: int = 0
    retrieve: int = 0
    generate: int = 0
    total: int = 0


class QueryRequest(BaseModel):
    question: str = Field(..., max_length=500)
    mode: Literal["auto", "vector", "graph", "hybrid"] = "auto"
    top_k: int = Field(default=8, ge=1, le=20)
    debug: bool = False


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationItem] = Field(default_factory=list)
    route: RouteInfo
    graph_paths: list[dict[str, Any]] = Field(default_factory=list)
    passages: list[dict[str, Any]] = Field(default_factory=list)
    validation: ValidationResult
    status: Literal["ok", "needs_clarification", "refused", "validation_failed", "error"]
    latency_ms: LatencyBreakdown
