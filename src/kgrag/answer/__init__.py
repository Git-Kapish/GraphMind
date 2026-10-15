"""Answer Generation and Mechanical Citation Resolution Package (PRD §7.4, Milestone M6)."""

from kgrag.answer.context import EvidenceItem, EvidenceRegistry, assemble_context
from kgrag.answer.generator import GenerationOutcome, generate_grounded_answer
from kgrag.answer.pipeline import GroundedAnswerPipeline, GroundedAnswerResult
from kgrag.answer.validator import (
    CitationValidationResult,
    ResolvedCitation,
    parse_citation_labels,
    validate_citations,
)
from kgrag.answer.verbalizer import VerbalizedFact, verbalize_graph_path, verbalize_graph_paths

__all__ = [
    "EvidenceItem",
    "EvidenceRegistry",
    "assemble_context",
    "VerbalizedFact",
    "verbalize_graph_path",
    "verbalize_graph_paths",
    "CitationValidationResult",
    "ResolvedCitation",
    "parse_citation_labels",
    "validate_citations",
    "GenerationOutcome",
    "generate_grounded_answer",
    "GroundedAnswerResult",
    "GroundedAnswerPipeline",
]
