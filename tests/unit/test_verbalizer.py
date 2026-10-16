"""Unit tests for Graph Path Verbalization (PRD §7.4, FR-4.1, Milestone M6)."""

from kgrag.answer.verbalizer import verbalize_graph_path
from kgrag.retrieval.engine import GraphEvidenceItem, GraphPathResult


def test_verbalize_neighbors():
    """Verify neighbors path verbalization generates accurate natural language statement."""
    path = GraphPathResult(
        template_id="neighbors",
        nodes=["nvidia", "microsoft"],
        relations=["PARTNERS_WITH"],
        observation_ids=["obs_123"],
        evidence=[
            GraphEvidenceItem(
                observation_id="obs_123",
                chunk_id="chunk_001",
                evidence_quote="NVIDIA partnered with Microsoft on AI infrastructure.",
                relation_type="PARTNERS_WITH",
            )
        ],
        metadata={"source": "nvidia", "target": "microsoft", "relation": "PARTNERS_WITH"},
    )
    fact = verbalize_graph_path(path)
    assert "nvidia partnered with microsoft" in fact.statement.lower()
    assert fact.observation_ids == ["obs_123"]
    assert "chunk_001" in fact.source_chunks


def test_verbalize_two_hop():
    """Verify two_hop path verbalization connects intermediate and target cleanly."""
    path = GraphPathResult(
        template_id="two_hop",
        nodes=["nvidia", "microsoft", "worldwide"],
        relations=["PARTNERS_WITH", "OPERATES_IN"],
        observation_ids=["obs_1", "obs_2"],
        metadata={
            "source": "nvidia",
            "intermediate": "microsoft",
            "target": "worldwide",
            "relation_1": "PARTNERS_WITH",
            "relation_2": "OPERATES_IN",
        },
    )
    fact = verbalize_graph_path(path)
    assert "nvidia partnered with microsoft, which operates in worldwide." in fact.statement.lower()
    assert len(fact.observation_ids) == 2


def test_verbalize_shared_neighbors():
    """Verify shared_neighbors verbalization produces comparative statements."""
    path = GraphPathResult(
        template_id="shared_neighbors",
        nodes=["nvidia", "computer hardware companies", "microsoft"],
        relations=["COMPETES_IN", "COMPETES_IN"],
        metadata={
            "entity_1": "nvidia",
            "shared_entity": "computer hardware companies",
            "entity_2": "microsoft",
            "relation_1": "COMPETES_IN",
            "relation_2": "COMPETES_IN",
        },
    )
    fact = verbalize_graph_path(path)
    assert (
        "both nvidia and microsoft competes in market sector computer hardware companies."
        in fact.statement.lower()
    )


def test_verbalize_count_by_relation():
    """Verify count_by_relation verbalization summarizes entity counts and samples."""
    path = GraphPathResult(
        template_id="count_by_relation",
        nodes=["broadcom"],
        relations=["SUBSIDIARY_OF"],
        metadata={
            "entity": "broadcom",
            "relation": "SUBSIDIARY_OF",
            "entity_count": 10,
            "sample_entities": ["VMware", "CA Technologies", "Symantec"],
        },
    )
    fact = verbalize_graph_path(path)
    assert (
        "broadcom has 10 distinct canonical operates as a subsidiary of relationships"
        in fact.statement.lower()
    )
    assert "vmware" in fact.statement.lower()


def test_verbalize_officers_of():
    """Verify officers_of verbalization produces clear role statements."""
    path = GraphPathResult(
        template_id="officers_of",
        nodes=["Jensen Huang", "NVIDIA"],
        relations=["OFFICER_OF"],
        metadata={"officer_name": "Jensen Huang", "company_name": "NVIDIA"},
    )
    fact = verbalize_graph_path(path)
    assert (
        "jensen huang serves as an evidenced executive officer of nvidia." in fact.statement.lower()
    )
