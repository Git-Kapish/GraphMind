"""Unit tests for deterministic Exhibit 21 subsidiary parser (PRD FR-1.1, FR-1.3 rule 11)."""

from kgrag.extract.exhibit21 import parse_exhibit21_subsidiaries


def test_parse_exhibit21_subsidiaries():
    parent = "NVIDIA Corporation"
    accession = "0001045810-26-000021"
    subs = [
        {"name": "Mellanox Technologies, Ltd", "jurisdiction": "Israel"},
        {"name": "NVIDIA Singapore Pte Ltd", "jurisdiction": "Singapore"},
    ]

    observations = parse_exhibit21_subsidiaries(parent, accession, subs)
    assert len(observations) == 4  # 2 SUBSIDIARY_OF + 2 OPERATES_IN

    sub_relations = [o for o in observations if o.relation_type == "SUBSIDIARY_OF"]
    assert len(sub_relations) == 2
    assert sub_relations[0].head_surface == "Mellanox Technologies, Ltd"
    assert sub_relations[0].head_type == "Company"
    assert sub_relations[0].tail_surface == parent
    assert sub_relations[0].tail_type == "Company"
    assert sub_relations[0].extraction_method == "parser"
    assert sub_relations[0].evidence_verified is True

    op_relations = [o for o in observations if o.relation_type == "OPERATES_IN"]
    assert len(op_relations) == 2
    assert op_relations[0].head_surface == "Mellanox Technologies, Ltd"
    assert op_relations[0].head_type == "Company"
    assert op_relations[0].tail_surface == "Israel"
    assert op_relations[0].tail_type == "Location"
