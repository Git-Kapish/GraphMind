"""Unit tests for entity resolution normalizer (PRD §8, Milestone M2.5/M3)."""

import pytest
from kgrag.resolve.resolver import normalize_name


def test_normalize_name_known_aliases():
    canon, eid = normalize_name("nvidia corp", "Company")
    assert canon == "NVIDIA Corporation"
    assert eid.startswith("ent_")

    canon, eid = normalize_name("Taiwan Semiconductor (TSMC)", "Company")
    assert canon == "Taiwan Semiconductor Manufacturing Company"
    assert eid.startswith("ent_")

    canon, eid = normalize_name("cisco systems, inc.", "Company")
    assert canon == "Cisco Systems, Inc."

    canon, eid = normalize_name("openai opco, llc", "Company")
    assert canon == "OpenAI"


def test_normalize_name_legal_suffix_stripping():
    canon, eid = normalize_name("Fabless Design Labs, Inc.", "Company")
    assert canon == "Fabless Design Labs"

    canon, eid = normalize_name("Global Foundry Services LLC", "Company")
    assert canon == "Global Foundry Services"

    canon, eid = normalize_name("Silicon Technologies Ltd.", "Company")
    assert canon == "Silicon Technologies"


def test_normalize_name_person_and_location():
    canon, eid = normalize_name("Jensen Huang", "Person")
    assert canon == "Jensen Huang"
    assert eid.startswith("ent_")

    canon, eid = normalize_name("Santa Clara, California", "Location")
    assert canon == "Santa Clara, California"


def test_normalize_name_deterministic_id():
    _, eid1 = normalize_name("Broadcom Inc.", "Company")
    _, eid2 = normalize_name("broadcom", "Company")
    assert eid1 == eid2  # Both resolve to same canonical entity ID!


def test_get_review_queue_and_merge_history():
    from kgrag.resolve.resolver import get_merge_history, get_review_queue

    history = get_merge_history(limit=10)
    assert isinstance(history, list)
    if history:
        item = history[0]
        assert "source_entity_id" in item
        assert "canonical_entity_id" in item
        assert "decision" in item
        assert "method" in item

    queue = get_review_queue()
    assert isinstance(queue, list)
    for q in queue:
        assert q["decision"] == "needs_review" or "reviewer_note" in q

