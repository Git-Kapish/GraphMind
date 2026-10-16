"""Context Assembly and Request-Scoped Evidence Registry (PRD §7.4, FR-4.2).

Assembles dual evidence sources into structured sections:
1. GRAPH FACTS ([G1], [G2], ...)
2. RETRIEVED PASSAGES ([P1], [P2], ...)

Maintains an internal request-scoped EvidenceRegistry mapping each label to its verified
chunk ID, observation IDs, document metadata, and quotes. Enforces context token budget.
"""

import logging
from typing import Literal

from pydantic import BaseModel, Field

from kgrag.answer.verbalizer import verbalize_graph_paths
from kgrag.config import get_settings
from kgrag.data.chunker import estimate_tokens
from kgrag.retrieval.engine import GraphPathResult, VectorPassageResult

logger = logging.getLogger(__name__)


class EvidenceItem(BaseModel):
    """Metadata and provenance for a single cited evidence item in the registry."""

    label: str  # e.g., "[G1]", "[P1]"
    chunk_id: str
    doc_id: str = ""
    company: str = ""
    ticker: str = ""
    section_path: str = ""
    text_snippet: str = ""
    evidence_quote: str = ""
    observation_ids: list[str] = Field(default_factory=list)
    source_type: Literal["graph", "vector"] = "vector"


class EvidenceRegistry:
    """Request-scoped registry mapping citation labels to verified chunk provenance (PRD FR-4.2)."""

    def __init__(self) -> None:
        self._items: dict[str, EvidenceItem] = {}

    def register(self, item: EvidenceItem) -> None:
        """Register an evidence item under its citation label."""
        self._items[item.label] = item

    def get(self, label: str) -> EvidenceItem | None:
        """Retrieve evidence item by label (e.g. '[G1]' or '[P2]')."""
        return self._items.get(label)

    def contains(self, label: str) -> bool:
        """Check if label exists in registry."""
        return label in self._items

    def get_valid_labels(self) -> list[str]:
        """Return all valid citation labels registered for this request."""
        return list(self._items.keys())

    def get_chunk_ids(self) -> set[str]:
        """Return set of all chunk IDs associated with registered citations."""
        return {item.chunk_id for item in self._items.values() if item.chunk_id}

    def items(self) -> list[EvidenceItem]:
        """Return all registered evidence items."""
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)


def assemble_context(
    graph_paths: list[GraphPathResult] | None = None,
    vector_passages: list[VectorPassageResult] | None = None,
    max_tokens: int | None = None,
) -> tuple[str, EvidenceRegistry]:
    """Assemble GRAPH FACTS and RETRIEVED PASSAGES into prompt context with registry (PRD FR-4.2)."""
    settings = get_settings()
    budget = max_tokens or settings.query.context_token_budget
    registry = EvidenceRegistry()

    graph_sections: list[str] = []
    vector_sections: list[str] = []

    # 1. Assemble Graph Facts ([G1], [G2], ...)
    if graph_paths:
        verbalized = verbalize_graph_paths(graph_paths)
        for idx, fact in enumerate(verbalized, 1):
            label = f"[G{idx}]"
            primary_chunk = (
                fact.source_chunks[0]
                if fact.source_chunks
                else (fact.evidence[0].chunk_id if fact.evidence else "unknown_chunk")
            )
            primary_quote = fact.evidence[0].evidence_quote if fact.evidence else ""
            primary_company = fact.evidence[0].filing_company or "" if fact.evidence else ""
            primary_ticker = fact.evidence[0].filing_ticker or "" if fact.evidence else ""

            registry.register(
                EvidenceItem(
                    label=label,
                    chunk_id=primary_chunk,
                    company=primary_company,
                    ticker=primary_ticker,
                    evidence_quote=primary_quote,
                    text_snippet=fact.statement,
                    observation_ids=fact.observation_ids,
                    source_type="graph",
                )
            )

            quote_clause = f' (Filing evidence: "{primary_quote}")' if primary_quote else ""
            graph_sections.append(f"{label} {fact.statement}{quote_clause}")

    # 2. Assemble Retrieved Passages ([P1], [P2], ...) with Deduplication
    if vector_passages:
        seen_chunks: set[str] = set()
        p_idx = 1
        for vp in vector_passages:
            if vp.chunk_id in seen_chunks:
                continue
            seen_chunks.add(vp.chunk_id)

            label = f"[P{p_idx}]"
            clean_text = vp.text.strip().replace("\r\n", "\n")

            registry.register(
                EvidenceItem(
                    label=label,
                    chunk_id=vp.chunk_id,
                    doc_id=vp.doc_id,
                    company=vp.company,
                    ticker=vp.ticker,
                    section_path=vp.section_path,
                    text_snippet=clean_text,
                    evidence_quote="",
                    source_type="vector",
                )
            )

            header = (
                f"{label} ({vp.company}, Ticker: {vp.ticker or 'N/A'}, Section: {vp.section_path}):"
            )
            passage_block = f'{header}\n"{clean_text}"'
            vector_sections.append(passage_block)
            p_idx += 1

    # 3. Format Combined Context Sections
    context_parts: list[str] = []

    if graph_sections:
        context_parts.append("### GRAPH FACTS (Structured Enterprise Relationships)")
        context_parts.append("\n".join(graph_sections))

    if vector_sections:
        context_parts.append("### RETRIEVED PASSAGES (Source Filing Text)")
        context_parts.append("\n\n".join(vector_sections))

    full_context = "\n\n".join(context_parts)

    # Respect Context Budget
    if estimate_tokens(full_context) > budget:
        logger.warning(
            "Context exceeded budget (%d > %d tokens). Truncating passages.",
            estimate_tokens(full_context),
            budget,
        )
        # Keep graph facts intact, truncate vector passages to fit budget
        kept_passages: list[str] = []
        base_tokens = estimate_tokens(
            "\n\n".join(["### GRAPH FACTS", "\n".join(graph_sections), "### RETRIEVED PASSAGES"])
        )
        current_tokens = base_tokens
        for p in vector_sections:
            p_tok = estimate_tokens(p)
            if current_tokens + p_tok <= budget:
                kept_passages.append(p)
                current_tokens += p_tok
            else:
                break
        context_parts = []
        if graph_sections:
            context_parts.append("### GRAPH FACTS (Structured Enterprise Relationships)")
            context_parts.append("\n".join(graph_sections))
        if kept_passages:
            context_parts.append("### RETRIEVED PASSAGES (Source Filing Text)")
            context_parts.append("\n\n".join(kept_passages))
        full_context = "\n\n".join(context_parts)

    return full_context, registry
