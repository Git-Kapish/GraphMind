"""Integration test running Milestone M2.5 Thin Vertical Slice (PRD §0 rule 13, §14)."""

from kgrag.slice_demo import run_vertical_slice


def test_vertical_slice_gate_passes():
    outcome = run_vertical_slice()
    assert outcome["total_questions"] == 10
    assert outcome["graph_score"] >= 9
    assert outcome["multihop_graph_wins"] >= 1
    assert outcome["gate_passed"] is True
