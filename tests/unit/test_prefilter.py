"""Unit tests for ChunkPreFilter (PRD §5.7)."""

import pytest
from kgrag.extract.prefilter import ChunkPreFilter


def test_prefilter_empty_text():
    prefilter = ChunkPreFilter()
    should, reason = prefilter.should_extract("")
    assert should is False
    assert reason == "empty_text"


def test_prefilter_matches_relation_cue():
    prefilter = ChunkPreFilter()
    text = "In 2024, our primary supplier was responsible for delivering high-performance wafer components."
    should, reason = prefilter.should_extract(text)
    assert should is True
    assert "relation_cue" in reason
    assert "supplier" in reason


def test_prefilter_matches_customer_cue():
    prefilter = ChunkPreFilter()
    text = "We depend on major OEM customers for a substantial portion of our net revenue."
    should, reason = prefilter.should_extract(text)
    assert should is True
    assert "relation_cue" in reason


def test_prefilter_gazetteer_condition():
    custom_cfg = {
        "relation_cues": ["unrelatedcue123"],
        "gazetteer": {
            "min_entity_mentions": 2,
            "seed_entities": [
                {"name": "NVIDIA", "aliases": ["NVDA"]},
                {"name": "Intel", "aliases": ["INTC"]},
                {"name": "TSMC", "aliases": []},
            ],
        },
    }
    prefilter = ChunkPreFilter(config=custom_cfg)

    # 1 entity mention -> should NOT extract
    text_one = "This paragraph talks about NVIDIA and its GPU architecture in general terms."
    should_1, reason_1 = prefilter.should_extract(text_one)
    assert should_1 is False

    # 2 entity mentions -> should extract
    text_two = "This paragraph discusses how NVIDIA and TSMC collaborate together."
    should_2, reason_2 = prefilter.should_extract(text_two)
    assert should_2 is True
    assert "gazetteer_count:2" in reason_2


def test_prefilter_filters_generic_text():
    custom_cfg = {
        "relation_cues": ["supplier", "customer", "acquired"],
        "gazetteer": {"min_entity_mentions": 2, "seed_entities": []},
    }
    prefilter = ChunkPreFilter(config=custom_cfg)
    generic_text = "Operating expenses increased primarily due to higher marketing costs and corporate office leases."
    should, reason = prefilter.should_extract(generic_text)
    assert should is False
    assert reason == "filtered_no_cue_or_gazetteer"
