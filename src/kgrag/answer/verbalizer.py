"""Graph Path Verbalization into Evidence-Grounded Statements (PRD §7.4, FR-4.1).

Translates structured GraphPathResult objects into precise, human-readable natural language
statements, retaining 100% provenance linkage to observation IDs and source chunk IDs.
"""

from pydantic import BaseModel, Field

from kgrag.retrieval.engine import GraphEvidenceItem, GraphPathResult

RELATION_PHRASES: dict[str, str] = {
    "PARTNERS_WITH": "partnered with",
    "COMPETES_WITH": "competes with",
    "SUBSIDIARY_OF": "operates as a subsidiary of",
    "OFFICER_OF": "serves as an officer of",
    "ACQUIRED": "acquired",
    "INVESTS_IN": "invests in",
    "SUPPLIES_TO": "supplies to",
    "MANUFACTURED_BY": "is manufactured by",
    "OFFERS": "offers product line",
    "BUILT_ON": "is built on",
    "COMPETES_IN": "competes in market sector",
    "OPERATES_IN": "operates in",
    "SUBJECT_TO": "is subject to",
    "HEADQUARTERED_IN": "is headquartered in",
}


def _phrase(rel: str) -> str:
    """Format relation type into a natural English phrase."""
    return RELATION_PHRASES.get(rel.upper(), rel.lower().replace("_", " "))


class VerbalizedFact(BaseModel):
    """A natural language statement derived from a graph traversal with attached evidence."""

    statement: str
    template_id: str
    nodes: list[str] = Field(default_factory=list)
    relations: list[str] = Field(default_factory=list)
    observation_ids: list[str] = Field(default_factory=list)
    source_chunks: list[str] = Field(default_factory=list)
    evidence: list[GraphEvidenceItem] = Field(default_factory=list)


def verbalize_graph_path(path: GraphPathResult) -> VerbalizedFact:
    """Convert a single GraphPathResult into a VerbalizedFact statement (PRD FR-4.1)."""
    tid = path.template_id
    meta = path.metadata
    nodes = path.nodes
    relations = path.relations

    statement = ""

    # 1. Template: neighbors
    if tid == "neighbors":
        src = meta.get("source") or (nodes[0] if len(nodes) > 0 else "Entity")
        tgt = meta.get("target") or (nodes[1] if len(nodes) > 1 else "target entity")
        rel = meta.get("relation") or (relations[0] if relations else "connected to")
        statement = f"{src} {_phrase(rel)} {tgt}."

    # 2. Template: two_hop
    elif tid == "two_hop":
        src = meta.get("source") or (nodes[0] if len(nodes) > 0 else "Entity")
        mid = meta.get("intermediate") or (nodes[1] if len(nodes) > 1 else "intermediate entity")
        tgt = meta.get("target") or (nodes[2] if len(nodes) > 2 else "target entity")
        r1 = meta.get("relation_1") or (relations[0] if len(relations) > 0 else "linked to")
        r2 = meta.get("relation_2") or (relations[1] if len(relations) > 1 else "linked to")
        statement = f"{src} {_phrase(r1)} {mid}, which {_phrase(r2)} {tgt}."

    # 3. Template: path_between
    elif tid == "path_between":
        path_nodes = meta.get("path_nodes") or nodes
        path_rels = meta.get("path_relations") or relations
        if len(path_nodes) >= 2 and len(path_rels) >= 1:
            steps = []
            for i in range(len(path_rels)):
                u = path_nodes[i]
                v = path_nodes[i + 1]
                r = path_rels[i]
                steps.append(f"{u} {_phrase(r)} {v}")
            statement = (
                f"Path between {path_nodes[0]} and {path_nodes[-1]} ({len(path_rels)} hops): "
                + "; then ".join(steps)
                + "."
            )
        else:
            statement = f"Connection exists between {' and '.join(nodes)}."

    # 4. Template: shared_neighbors
    elif tid == "shared_neighbors":
        e1 = meta.get("entity_1") or (nodes[0] if len(nodes) > 0 else "Entity 1")
        shared = meta.get("shared_entity") or (nodes[1] if len(nodes) > 1 else "shared entity")
        e2 = meta.get("entity_2") or (nodes[2] if len(nodes) > 2 else "Entity 2")
        r1 = meta.get("relation_1") or (relations[0] if len(relations) > 0 else "connected to")
        r2 = meta.get("relation_2") or (relations[1] if len(relations) > 1 else "connected to")

        if r1.upper() == r2.upper():
            statement = f"Both {e1} and {e2} {_phrase(r1)} {shared}."
        else:
            statement = f"{e1} {_phrase(r1)} {shared}, while {e2} {_phrase(r2)} {shared}."

    # 5. Template: count_by_relation
    elif tid == "count_by_relation":
        ent = meta.get("entity") or (nodes[0] if nodes else "Entity")
        cnt = meta.get("entity_count", 0)
        rel = meta.get("relation", "connected")
        samples = meta.get("sample_entities", [])
        sample_str = f" (including {', '.join(samples[:5])})" if samples else ""
        statement = f"{ent} has {cnt} distinct canonical {_phrase(rel)} relationships documented in filings{sample_str}."

    # 6. Template: top_connected
    elif tid == "top_connected":
        ent = meta.get("entity") or (nodes[0] if nodes else "Entity")
        deg = meta.get("degree", 0)
        samples = meta.get("sample_connections", [])
        sample_str = f" (sample connections: {', '.join(samples[:4])})" if samples else ""
        statement = f"{ent} has degree centrality of {deg} across corporate filings{sample_str}."

    # 7. Template: officers_of
    elif tid == "officers_of":
        off = meta.get("officer_name") or (nodes[0] if len(nodes) > 0 else "Individual")
        co = meta.get("company_name") or (nodes[1] if len(nodes) > 1 else "Company")
        statement = f"{off} serves as an evidenced executive officer of {co}."

    # Fallback
    else:
        statement = f"Graph connection: {' -> '.join(nodes)}."

    # Collect source chunks
    source_chunks = list(meta.get("source_chunks", []))
    for ev in path.evidence:
        if ev.chunk_id and ev.chunk_id not in source_chunks:
            source_chunks.append(ev.chunk_id)

    return VerbalizedFact(
        statement=statement,
        template_id=tid,
        nodes=nodes,
        relations=relations,
        observation_ids=path.observation_ids,
        source_chunks=source_chunks,
        evidence=path.evidence,
    )


def verbalize_graph_paths(paths: list[GraphPathResult]) -> list[VerbalizedFact]:
    """Convert multiple GraphPathResult objects into a list of VerbalizedFacts."""
    return [verbalize_graph_path(p) for p in paths]
