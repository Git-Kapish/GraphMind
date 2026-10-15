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
    question: str = Field(..., min_length=3, max_length=500)
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
    request_id: str = ""


class EntityDetailResponse(BaseModel):
    """Canonical entity detail and graph relationship overview (PRD §8)."""
    entity_id: str
    canonical_name: str
    type: str
    aliases: list[str] = Field(default_factory=list)
    degree: int = 0
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    absorbed_entities: list[str] = Field(default_factory=list)
    canonical_for: list[str] = Field(default_factory=list)


class ChunkObservationItem(BaseModel):
    observation_id: str
    head_surface: str
    relation_type: str
    tail_surface: str
    evidence_quote: str
    evidence_verified: bool = False


class ChunkDetailResponse(BaseModel):
    """Authoritative chunk text, document provenance, and extraction observations (PRD §8)."""
    chunk_id: str
    doc_id: str
    company: str
    ticker: str
    cik: str
    form_type: str
    fiscal_year: int
    filing_date: str
    accession: str
    section_path: str
    item: str
    text: str
    token_count: int
    entity_ids: list[str] = Field(default_factory=list)
    source_url: str
    observations_count: int = 0
    observations: list[ChunkObservationItem] = Field(default_factory=list)
