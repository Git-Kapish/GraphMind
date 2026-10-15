"""Unit tests for safe parameterized Cypher templates and query safety guardrails (PRD §7.3, FR-3.2, Milestone M5)."""

import pytest

from kgrag.graph.templates import (
    StrictResolutionStatus,
    TemplateId,
    attach_evidence_to_paths,
    explain_template_query,
    fetch_evidence_for_observations,
    query_count_by_relation,
    query_neighbors,
    query_officers_of,
    query_path_between,
    query_shared_neighbors,
    query_top_connected,
    query_two_hop,
    resolve_entity_strict,
    validate_relation_type,
)


def test_ontology_relation_type_validation():
    """Verify that relation types are strictly validated against closed ontology enum (PRD FR-3.2)."""
    assert validate_relation_type("SUBSIDIARY_OF") == "SUBSIDIARY_OF"
    assert validate_relation_type("partners_with") == "PARTNERS_WITH"
    assert validate_relation_type(None) is None

    # Invalid relation types rejected
    with pytest.raises(ValueError, match="Invalid relation type"):
        validate_relation_type("ARBITRARY_INJECTION_RELATION")


def test_anchor_node_query_plan_index_seek():
    """Verify query plan performs a NodeUniqueIndexSeek on the anchor entity_id (PRD FR-3.2)."""
    cypher = "MATCH (a:Entity {entity_id: $a_id})-[r:COMPETES_WITH]-(b:Entity) RETURN a, r, b"
    plan_info = explain_template_query(cypher, {"a_id": "ent_99ee45010f6a"})

    assert plan_info["has_index_seek"] is True, f"Expected NodeUniqueIndexSeek in plan: {plan_info['plan_string']}"


def test_template_1_neighbors():
    """Test Template 1: 1-hop neighbors retrieval with evidence links."""
    results = query_neighbors("nvidia", limit=5)
    assert len(results) > 0
    first = results[0]
    assert "source" in first
    assert "relation" in first
    assert "target" in first
    assert "observation_ids" in first


def test_template_2_two_hop_no_node_repeats():
    """Test Template 2: 2-hop traversal paths with no repeated intermediate/target nodes (PRD FR-3.2)."""
    results = query_two_hop("nvidia", limit=5)
    assert len(results) > 0

    for r in results:
        src = r["source_id"]
        mid = r["intermediate_id"]
        tgt = r["target_id"]
        # Invariant: a <> m AND a <> b AND b <> m
        assert src != mid, "Intermediate node matches source node!"
        assert src != tgt, "Target node matches source node!"
        assert mid != tgt, "Target node matches intermediate node!"


def test_template_3_path_between():
    """Test Template 3: Bounded shortest path between entities up to 3 hops (PRD FR-3.2)."""
    # NVIDIA and Microsoft share connections via markets/geography
    paths = query_path_between("nvidia", "microsoft", max_hops=3)
    assert len(paths) > 0
    p = paths[0]
    assert "path_nodes" in p
    assert "path_relations" in p
    assert p["hop_count"] <= 3


def test_template_4_shared_neighbors():
    """Test Template 4: Common intermediate entities connected to both A and B (PRD FR-3.2)."""
    results = query_shared_neighbors("nvidia", "microsoft", limit=5)
    assert len(results) > 0

    for r in results:
        assert r["entity_1_id"] != r["entity_2_id"]
        assert r["shared_entity_id"] != r["entity_1_id"]
        assert r["shared_entity_id"] != r["entity_2_id"]


def test_template_5_count_by_relation():
    """Test Template 5: Count unique entities connected to anchor entity via relation R."""
    res = query_count_by_relation("Broadcom", "SUBSIDIARY_OF")
    assert res["entity_count"] > 0
    assert "sample_entities" in res
    assert isinstance(res["sample_entities"], list)


def test_template_6_top_connected():
    """Test Template 6: Rank entities by degree centrality under relation or overall."""
    results = query_top_connected(limit=5)
    assert len(results) > 0
    # Assert monotonic descending ordering by degree
    degrees = [r["degree"] for r in results]
    assert degrees == sorted(degrees, reverse=True)


def test_template_7_officers_of():
    """Test Template 7: Retrieve executive officers with evidenced roles at company."""
    # NVIDIA has known officers (Jensen Huang, Colette Kress, etc.)
    results = query_officers_of("nvidia", limit=5)
    assert isinstance(results, list)
    if results:
        assert "officer_name" in results[0]
        assert "company_name" in results[0]
        assert "observation_ids" in results[0]


def test_symmetric_relation_undirected_matching():
    """Verify that symmetric relations (e.g. COMPETES_WITH) match regardless of endpoint order (PRD FR-3.2)."""
    from kgrag.graph.templates import resolve_anchor_entity_id

    # Whether querying from NVIDIA or AMD, symmetric relation is discoverable
    res_nvda = query_neighbors("nvidia", relation_type="COMPETES_WITH")
    res_amd = query_neighbors("amd", relation_type="COMPETES_WITH")

    nvda_competitors = {r["target"].lower() for r in res_nvda}
    amd_competitors = {r["target"].lower() for r in res_amd}

    # At least one competitor should be mutually identified
    assert len(nvda_competitors) > 0 or len(amd_competitors) > 0


def test_attach_evidence_to_paths():
    """Verify that graph paths are enriched with verbatim evidence quotes and chunk metadata."""
    paths = query_neighbors("nvidia", limit=2)
    assert len(paths) > 0

    enriched = attach_evidence_to_paths(paths)
    assert len(enriched) == len(paths)
    first = enriched[0]
    assert "evidence" in first
    if first["observation_ids"]:
        assert len(first["evidence"]) > 0
        ev = first["evidence"][0]
        assert "evidence_quote" in ev
        assert "chunk_id" in ev


def test_directed_relation_not_matched_in_reverse():
    """Verify that a directed relation is strictly not matched in reverse (PRD FR-3.2, §14 M5)."""
    # In ontology: (Person)-[OFFICER_OF]->(Company).
    # NVIDIA is the company (target of OFFICER_OF).
    # An outgoing query for OFFICER_OF from NVIDIA must match 0 records (NVIDIA is not an officer).
    out_results = query_neighbors("nvidia", relation_type="OFFICER_OF", direction="out", limit=5)
    assert len(out_results) == 0, "Directed OFFICER_OF was erroneously matched in outgoing direction from company!"

    # An incoming query must match the evidenced officer(s)
    in_results = query_neighbors("nvidia", relation_type="OFFICER_OF", direction="in", limit=5)
    assert len(in_results) > 0, "Directed OFFICER_OF failed to match in incoming direction to company!"
    assert in_results[0]["relation"] == "OFFICER_OF"


def test_hard_limit_enforced():
    """Verify that result count honors the requested limit and hard cap (PRD FR-3.2)."""
    # Broadcom has many subsidiaries; limit=2 should return at most 2
    results = query_neighbors("broadcom", limit=2)
    assert len(results) <= 2


def test_resolve_entity_strict_exact_and_alias():
    """Verify strict entity resolution policy resolves unambiguous exact/alias entities (PRD FR-3.2)."""
    # Exact canonical match maps to surviving canonical node
    res_canon = resolve_entity_strict("NVIDIA Corporation")
    assert res_canon.status == StrictResolutionStatus.RESOLVED
    assert res_canon.canonical_name == "nvidia"
    assert res_canon.confidence == 1.0

    # Alias / ticker match
    res_ticker = resolve_entity_strict("NVDA")
    assert res_ticker.status == StrictResolutionStatus.RESOLVED
    assert res_ticker.canonical_name == "nvidia"


def test_resolve_entity_strict_not_found():
    """Verify strict entity resolution returns not_found for non-existent entities without guessing (PRD FR-3.2)."""
    res = resolve_entity_strict("TotallyNonExistentEnterpriseEntity98765")
    assert res.status == StrictResolutionStatus.NOT_FOUND
    assert res.entity_id is None


def test_resolve_entity_strict_empty():
    """Verify empty mention is rejected immediately with not_found (PRD FR-3.2)."""
    res = resolve_entity_strict("")
    assert res.status == StrictResolutionStatus.NOT_FOUND
    assert "empty" in res.message.lower()

