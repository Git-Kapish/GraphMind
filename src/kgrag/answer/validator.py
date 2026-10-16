"""Mechanical Citation Resolution Validator (PRD §7.4, FR-4.4A).

Enforces the mechanical citation resolution invariant on every request:
1. Parses all citation labels ([G1], [P2], etc.).
2. Confirms every label exists in the request-scoped EvidenceRegistry.
3. Confirms every mapped chunk_id was actually retrieved for this request.
4. Rejects invented/hallucinated citation labels.
5. Produces actionable feedback for model regeneration if unresolved.
"""

import logging
import re

from pydantic import BaseModel, Field

from kgrag.answer.context import EvidenceItem, EvidenceRegistry
from kgrag.config import get_settings
from kgrag.llm.decisions import get_decision_client

logger = logging.getLogger(__name__)

CITATION_REGEX = re.compile(r"\[([GP]\d+)\]")

REFUSAL_CUES = [
    "insufficient evidence",
    "does not contain",
    "do not contain",
    "no information",
    "cannot answer",
    "provided evidence does not",
    "filings do not provide",
    "filings do not contain",
    "unable to determine",
    "unable to answer",
    "not mentioned in the provided",
]


class ResolvedCitation(BaseModel):
    """A verified, fully-resolved citation mapped to an actual retrieved chunk."""

    label: str
    chunk_id: str
    doc_id: str = ""
    company: str = ""
    ticker: str = ""
    section_path: str = ""
    text_snippet: str = ""
    evidence_quote: str = ""
    observation_ids: list[str] = Field(default_factory=list)
    source_type: str = "vector"
    supports_claim: str = "unknown"
    claim_support_confidence: float = 0.0


class CitationValidationResult(BaseModel):
    """Outcome of mechanical citation resolution validation."""

    is_valid: bool
    is_refusal: bool = False
    extracted_labels: list[str] = Field(default_factory=list)
    valid_labels: list[str] = Field(default_factory=list)
    invalid_labels: list[str] = Field(default_factory=list)
    resolved_citations: list[ResolvedCitation] = Field(default_factory=list)
    resolution_rate: float = 0.0
    feedback_message: str = ""


def parse_citation_labels(text: str) -> list[str]:
    """Extract all citation labels from response text preserving order."""
    matches = CITATION_REGEX.findall(text)
    return [f"[{m}]" for m in matches]


def is_refusal_text(text: str) -> bool:
    """Check if the generated response is an explicit refusal due to missing/insufficient evidence."""
    lower = text.lower()
    return any(cue in lower for cue in REFUSAL_CUES)


def validate_citations(
    answer_text: str,
    registry: EvidenceRegistry,
) -> CitationValidationResult:
    """Validate that 100% of citation labels resolve to retrieved chunks in the evidence registry (PRD FR-4.4A)."""
    labels = parse_citation_labels(answer_text)
    is_refusal = is_refusal_text(answer_text)

    # Case 1: Refusal Response
    if is_refusal:
        if not labels:
            return CitationValidationResult(
                is_valid=True,
                is_refusal=True,
                extracted_labels=[],
                valid_labels=[],
                invalid_labels=[],
                resolved_citations=[],
                resolution_rate=1.0,
                feedback_message="Valid refusal: evidence is missing or insufficient.",
            )

    # Case 2: Zero Citations on a Factual Answer
    if not labels:
        valid_opts = ", ".join(registry.get_valid_labels()) or "<none>"
        return CitationValidationResult(
            is_valid=False,
            is_refusal=False,
            extracted_labels=[],
            valid_labels=[],
            invalid_labels=[],
            resolved_citations=[],
            resolution_rate=0.0,
            feedback_message=(
                "Your answer did not cite any evidence labels. Every factual statement must cite "
                f"at least one evidence label in brackets (e.g. [G1], [P1]). Available labels: {valid_opts}."
            ),
        )

    # Case 3: Verify Each Citation Label against the Registry
    valid_labels: list[str] = []
    invalid_labels: list[str] = []
    resolved: list[ResolvedCitation] = []
    seen_labels: set[str] = set()

    for label in labels:
        item: EvidenceItem | None = registry.get(label)
        if item is not None and item.chunk_id:
            if label not in seen_labels:
                seen_labels.add(label)
                valid_labels.append(label)
                resolved.append(
                    ResolvedCitation(
                        label=item.label,
                        chunk_id=item.chunk_id,
                        doc_id=item.doc_id,
                        company=item.company,
                        ticker=item.ticker,
                        section_path=item.section_path,
                        text_snippet=item.text_snippet,
                        evidence_quote=item.evidence_quote,
                        observation_ids=item.observation_ids,
                        source_type=item.source_type,
                    )
                )
        else:
            if label not in invalid_labels:
                invalid_labels.append(label)

    total_citations = len(labels)
    resolution_rate = len(valid_labels) / total_citations if total_citations > 0 else 0.0

    if invalid_labels:
        valid_opts = ", ".join(registry.get_valid_labels()) or "<none>"
        invalid_str = ", ".join(invalid_labels)
        return CitationValidationResult(
            is_valid=False,
            is_refusal=is_refusal,
            extracted_labels=labels,
            valid_labels=valid_labels,
            invalid_labels=invalid_labels,
            resolved_citations=resolved,
            resolution_rate=resolution_rate,
            feedback_message=(
                f"The following citation labels are INVALID because they do not exist in the evidence registry: {invalid_str}. "
                f"You may ONLY cite valid labels from the supplied evidence: {valid_opts}. "
                "Please regenerate the answer citing ONLY valid evidence labels."
            ),
        )

    return CitationValidationResult(
        is_valid=True,
        is_refusal=is_refusal,
        extracted_labels=labels,
        valid_labels=valid_labels,
        invalid_labels=[],
        resolved_citations=resolved,
        resolution_rate=1.0,
        feedback_message="All citations successfully resolved to retrieved chunks.",
    )


def verify_claim_support(
    answer_text: str,
    resolved_citations: list[ResolvedCitation],
) -> list[ResolvedCitation]:
    """Verify claim support for each resolved citation using System One Mercury Decide (PRD §7.4)."""
    settings = get_settings()
    if not (settings.system_one.runtime == "openrouter" and settings.system_one.api_key):
        return resolved_citations

    decision_client = get_decision_client()
    for citation in resolved_citations:
        evidence = citation.evidence_quote or citation.text_snippet
        if not evidence:
            citation.supports_claim = "unsupported"
            citation.claim_support_confidence = 0.5
            continue
        try:
            decision, conf = decision_client.decide_claim_support(
                claim=answer_text, evidence=evidence
            )
            citation.supports_claim = decision
            citation.claim_support_confidence = conf
        except Exception as e:
            logger.warning(
                "System One claim support check failed for citation %s: %s", citation.label, e
            )
            citation.supports_claim = "unknown"
            citation.claim_support_confidence = 0.5

    return resolved_citations
