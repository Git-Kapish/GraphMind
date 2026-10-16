"""Dual Minimal Retrieval Engine integrating Safe Graph Templates and Vector Baseline (PRD §7.3, Milestone M5)."""

import logging
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from kgrag.graph.templates import (
    TemplateId,
    attach_evidence_to_paths,
    query_count_by_relation,
    query_neighbors,
    query_officers_of,
    query_path_between,
    query_shared_neighbors,
    query_top_connected,
    query_two_hop,
)
from kgrag.vector.embeddings import query_vector_baseline

logger = logging.getLogger(__name__)


class GraphEvidenceItem(BaseModel):
    observation_id: str
    chunk_id: str
    evidence_quote: str
    relation_type: str
    filing_company: str | None = None
    filing_ticker: str | None = None


class GraphPathResult(BaseModel):
    template_id: str
    nodes: list[str] = Field(default_factory=list)
    relations: list[str] = Field(default_factory=list)
    observation_ids: list[str] = Field(default_factory=list)
    evidence: list[GraphEvidenceItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorPassageResult(BaseModel):
    chunk_id: str
    doc_id: str
    company: str
    ticker: str
    section_path: str
    text: str
    cosine_similarity: float
    item: str | None = None


class RetrievalBundle(BaseModel):
    mode: Literal["graph", "vector", "dual"]
    query_text: str
    graph_paths: list[GraphPathResult] = Field(default_factory=list)
    vector_passages: list[VectorPassageResult] = Field(default_factory=list)
    latency_ms: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalEngine:
    """Minimal Dual Retrieval Engine executing safe graph templates and pgvector search (PRD §7.3)."""

    def retrieve_graph(
        self,
        template_id: TemplateId | str,
        entity_1: str | None = None,
        entity_2: str | None = None,
        relation_type: str | None = None,
        relation_2: str | None = None,
        limit: int = 20,
    ) -> list[GraphPathResult]:
        """Execute a parameterized safe Cypher template with evidence attachment (PRD FR-3.2)."""
        tid = TemplateId(template_id)
        raw_paths: list[dict[str, Any]] = []

        if tid in (
            TemplateId.NEIGHBORS,
            TemplateId.TWO_HOP,
            TemplateId.COUNT_BY_RELATION,
            TemplateId.OFFICERS_OF,
        ):
            if not entity_1:
                raise ValueError(f"{tid.value} template requires entity_1.")

        if tid == TemplateId.NEIGHBORS:
            raw_paths = query_neighbors(entity_1, relation_type=relation_type, limit=limit)
        elif tid == TemplateId.TWO_HOP:
            raw_paths = query_two_hop(
                entity_1, relation_1=relation_type, relation_2=relation_2, limit=limit
            )
        elif tid == TemplateId.SHARED_NEIGHBORS:
            if not entity_1 or not entity_2:
                raise ValueError("SHARED_NEIGHBORS template requires both entity_1 and entity_2.")
            raw_paths = query_shared_neighbors(
                entity_1, entity_2, relation_type=relation_type, limit=limit
            )
        elif tid == TemplateId.PATH_BETWEEN:
            if not entity_2:
                raise ValueError("PATH_BETWEEN template requires entity_2.")
            raw_paths = query_path_between(entity_1, entity_2, limit=limit)
        elif tid == TemplateId.COUNT_BY_RELATION:
            if not relation_type:
                raise ValueError("COUNT_BY_RELATION template requires relation_type.")
            res = query_count_by_relation(entity_1, relation_type=relation_type)
            raw_paths = [res]
        elif tid == TemplateId.TOP_CONNECTED:
            raw_paths = query_top_connected(relation_type=relation_type, limit=limit)
        elif tid == TemplateId.OFFICERS_OF:
            raw_paths = query_officers_of(entity_1, limit=limit)

        # Attach verbatim evidence quotes from PostgreSQL
        enriched = attach_evidence_to_paths(raw_paths)

        results: list[GraphPathResult] = []
        for p in enriched:
            evidence_items = [
                GraphEvidenceItem(
                    observation_id=ev["observation_id"],
                    chunk_id=ev["chunk_id"],
                    evidence_quote=ev["evidence_quote"],
                    relation_type=ev.get("relation_type", ""),
                    filing_company=ev.get("filing_company"),
                    filing_ticker=ev.get("filing_ticker"),
                )
                for ev in p.get("evidence", [])
            ]

            nodes = []
            for k in (
                "source",
                "intermediate",
                "target",
                "entity_1",
                "shared_entity",
                "entity_2",
                "officer_name",
                "company_name",
            ):
                if k in p and p[k] and p[k] not in nodes:
                    nodes.append(str(p[k]))
            if "path_nodes" in p:
                nodes = p["path_nodes"]

            relations = []
            for k in ("relation", "relation_1", "relation_2"):
                if k in p and p[k]:
                    relations.append(str(p[k]))
            if "path_relations" in p:
                relations = p["path_relations"]

            results.append(
                GraphPathResult(
                    template_id=tid.value,
                    nodes=nodes,
                    relations=relations,
                    observation_ids=p.get("observation_ids", []),
                    evidence=evidence_items,
                    metadata={
                        k: v for k, v in p.items() if k not in ("evidence", "observation_ids")
                    },
                )
            )

        return results

    def retrieve_vector(
        self,
        query_text: str,
        top_k: int = 5,
        item_filter: str | None = None,
        ticker_filter: str | None = None,
    ) -> list[VectorPassageResult]:
        """Execute pgvector baseline cosine search (PRD FR-2.1)."""
        raw_chunks = query_vector_baseline(
            query_text=query_text,
            top_k=top_k,
            item_filter=item_filter,
            ticker_filter=ticker_filter,
        )

        return [
            VectorPassageResult(
                chunk_id=c["chunk_id"],
                doc_id=c["doc_id"],
                company=c["company"],
                ticker=c["ticker"],
                section_path=c["section_path"],
                text=c["text"],
                cosine_similarity=float(c["cosine_similarity"]),
                item=c.get("item"),
            )
            for c in raw_chunks
        ]

    def retrieve_dual(
        self,
        query_text: str,
        template_id: TemplateId | str | None = None,
        entity_1: str | None = None,
        entity_2: str | None = None,
        relation_type: str | None = None,
        top_k: int = 5,
    ) -> RetrievalBundle:
        """Execute unified dual retrieval combining safe graph templates and pgvector passages (PRD §7.3)."""
        t0 = time.perf_counter()
        latencies: dict[str, int] = {}

        # 1. Vector Retrieval
        t_vec_0 = time.perf_counter()
        passages = self.retrieve_vector(query_text, top_k=top_k)
        latencies["vector_ms"] = int((time.perf_counter() - t_vec_0) * 1000)

        # 2. Graph Retrieval (if template specified or inferred)
        graph_paths: list[GraphPathResult] = []
        if template_id and entity_1:
            t_graph_0 = time.perf_counter()
            graph_paths = self.retrieve_graph(
                template_id=template_id,
                entity_1=entity_1,
                entity_2=entity_2,
                relation_type=relation_type,
                limit=top_k,
            )
            latencies["graph_ms"] = int((time.perf_counter() - t_graph_0) * 1000)

        latencies["total_ms"] = int((time.perf_counter() - t0) * 1000)

        mode = "dual" if (graph_paths and passages) else ("graph" if graph_paths else "vector")

        return RetrievalBundle(
            mode=mode,
            query_text=query_text,
            graph_paths=graph_paths,
            vector_passages=passages,
            latency_ms=latencies,
            metadata={"template_id": template_id, "entity_1": entity_1, "entity_2": entity_2},
        )
