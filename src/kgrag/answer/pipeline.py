"""End-to-End Grounded Answer Generation Pipeline (PRD §7.4, Milestone M6).

Orchestrates:
1. Context assembly & request-scoped evidence registration.
2. Grounded LLM generation with citation enforcement.
3. Mechanical citation resolution validation with feedback retry loops.
4. Ambiguity / clarification and safe refusal handling.
"""

import logging
import time
from typing import Any, Literal
from pydantic import BaseModel, Field

from kgrag.answer.context import EvidenceRegistry, assemble_context
from kgrag.answer.generator import GenerationOutcome, generate_grounded_answer
from kgrag.answer.validator import ResolvedCitation
from kgrag.graph.templates import StrictResolutionStatus, TemplateId, resolve_entity_strict
from kgrag.retrieval.engine import (
    GraphPathResult,
    RetrievalBundle,
    RetrievalEngine,
    VectorPassageResult,
)

logger = logging.getLogger(__name__)


class GroundedAnswerResult(BaseModel):
    """Complete, fully verified response with mechanical citations and provenance (PRD §7.4, §14)."""
    question: str
    answer: str
    status: Literal["answered", "refusal", "needs_clarification", "validation_failed"]
    citations: list[ResolvedCitation] = Field(default_factory=list)
    citation_resolution_rate: float = 1.0
    retries_used: int = 0
    latency_ms: dict[str, int] = Field(default_factory=dict)
    retrieval_bundle: RetrievalBundle | None = None
    message: str = ""


class GroundedAnswerPipeline:
    """Pipeline coordinating retrieval, verbalization, context assembly, generation, and citation validation."""

    def __init__(self, engine: RetrievalEngine | None = None, llm: Any | None = None) -> None:
        self.engine = engine or RetrievalEngine()
        self.llm = llm

    def answer_question(
        self,
        question: str,
        template_id: TemplateId | str | None = None,
        entity_1: str | None = None,
        entity_2: str | None = None,
        relation_type: str | None = None,
        top_k: int = 5,
        max_retries: int = 2,
    ) -> GroundedAnswerResult:
        """Execute end-to-end grounded answer generation for a user query (PRD §7.4)."""
        t0 = time.perf_counter()
        latencies: dict[str, int] = {}

        # 1. Ambiguity check on anchor entities if supplied (PRD FR-4.5)
        if entity_1:
            res_e1 = resolve_entity_strict(entity_1)
            if res_e1.status == StrictResolutionStatus.NEEDS_CLARIFICATION:
                return GroundedAnswerResult(
                    question=question,
                    answer=f"Entity mention '{entity_1}' is ambiguous. Please clarify which entity you mean.",
                    status="needs_clarification",
                    citations=[],
                    citation_resolution_rate=1.0,
                    retries_used=0,
                    latency_ms={"total_ms": int((time.perf_counter() - t0) * 1000)},
                    message=res_e1.message,
                )

        if entity_2:
            res_e2 = resolve_entity_strict(entity_2)
            if res_e2.status == StrictResolutionStatus.NEEDS_CLARIFICATION:
                return GroundedAnswerResult(
                    question=question,
                    answer=f"Entity mention '{entity_2}' is ambiguous. Please clarify which entity you mean.",
                    status="needs_clarification",
                    citations=[],
                    citation_resolution_rate=1.0,
                    latency_ms={"total_ms": int((time.perf_counter() - t0) * 1000)},
                    message=res_e2.message,
                )

        # 2. Retrieval Execution
        t_ret_0 = time.perf_counter()
        bundle = self.engine.retrieve_dual(
            query_text=question,
            template_id=template_id,
            entity_1=entity_1,
            entity_2=entity_2,
            relation_type=relation_type,
            top_k=top_k,
        )
        latencies.update(bundle.latency_ms)
        latencies["retrieval_total_ms"] = int((time.perf_counter() - t_ret_0) * 1000)

        # 3. Context Assembly & Evidence Registration
        t_ctx_0 = time.perf_counter()
        context_text, registry = assemble_context(
            graph_paths=bundle.graph_paths,
            vector_passages=bundle.vector_passages,
        )
        latencies["context_assembly_ms"] = int((time.perf_counter() - t_ctx_0) * 1000)

        # 4. Grounded Generation & Mechanical Citation Validation
        t_gen_0 = time.perf_counter()
        outcome = generate_grounded_answer(
            question=question,
            context_text=context_text,
            registry=registry,
            max_retries=max_retries,
            llm=self.llm,
        )
        latencies["generation_ms"] = int((time.perf_counter() - t_gen_0) * 1000)
        latencies["total_pipeline_ms"] = int((time.perf_counter() - t0) * 1000)

        return GroundedAnswerResult(
            question=question,
            answer=outcome.answer,
            status=outcome.status,
            citations=outcome.citations,
            citation_resolution_rate=outcome.resolution_rate,
            retries_used=outcome.retries_used,
            latency_ms=latencies,
            retrieval_bundle=bundle,
            message=outcome.validation.feedback_message if outcome.validation else "",
        )
