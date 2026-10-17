"""Deterministic demonstration fixtures and test cases for GraphMind (PRD §8, Milestone M10).

Provides verified baseline and hybrid execution artifacts for representative multi-hop
SEC 10-K questions, ensuring the technical demonstration can run and be inspected
even in environments without active database or model instances.
"""

# Representative Multi-Hop Question from Benchmark Set (M10_Q31)
DEMO_QUESTION_ID = "M10_Q31"
DEMO_QUESTION_TEXT = "Is Mellanox Technologies connected to NVIDIA, and what is their relationship?"
DEMO_CATEGORY = "multi_hop"
DEMO_HOP_COUNT = 2

# Dual Evidence Registry Fixtures
VERIFIED_GRAPH_FACTS = [
    {
        "label": "[G1]",
        "subject": "Mellanox Technologies, Ltd.",
        "relation": "SUBSIDIARY_OF",
        "target": "NVIDIA Corporation",
        "chunk_id": "0001045810-24-000029:exhibit21:0000",
        "evidence_quote": "Mellanox Technologies, Ltd., an Israeli company, is a wholly owned subsidiary of NVIDIA Corporation.",
    }
]

VERIFIED_VECTOR_PASSAGES = [
    {
        "label": "[P1]",
        "chunk_id": "0001045810-24-000029:item1:0003",
        "company": "NVIDIA Corporation",
        "ticker": "NVDA",
        "section": "Item 1. Business - Accelerated Networking",
        "snippet": "In April 2020, NVIDIA Corporation completed its acquisition of Mellanox Technologies, Ltd. for $6.9 billion. Mellanox networking solutions, including InfiniBand and Ethernet, are integrated into NVIDIA's Data Center platforms.",
    },
    {
        "label": "[P2]",
        "chunk_id": "0001045810-24-000029:exhibit21:0000",
        "company": "NVIDIA Corporation",
        "ticker": "NVDA",
        "section": "Exhibit 21. Subsidiaries of the Registrant",
        "snippet": "List of Subsidiaries: Mellanox Technologies, Ltd. (Israel); NVIDIA Singapore Development Pte. Ltd. (Singapore); NVIDIA GmbH (Germany).",
    },
]

# Grounded Answers & Citations
HYBRID_DEMO_ANSWER = (
    "Mellanox Technologies is a wholly owned operating subsidiary of NVIDIA Corporation [G1]. "
    "NVIDIA completed its acquisition of Mellanox in April 2020, integrating its InfiniBand and Ethernet "
    "networking products into NVIDIA's Data Center business [P1], as documented in NVIDIA's Exhibit 21 "
    "subsidiary disclosures [P2]."
)

BASELINE_DEMO_ANSWER = (
    "Mellanox Technologies is mentioned in connection with NVIDIA's Data Center segment and networking "
    "products [P1]. The filings discuss InfiniBand solutions, but dense semantic search alone did not "
    "directly retrieve the full parent-subsidiary traversal."
)

# Intentional Test Fixture for Mechanical Citation Failure Demonstration
# Cites nonexistent label [P99] to prove the mechanical validator catches hallucinated citations
INTENTIONAL_INVALID_CITATION_ANSWER = (
    "Mellanox Technologies is a subsidiary of NVIDIA Corporation [G1] and was acquired for $6.9 billion [P1], "
    "with additional undisclosed terms documented in confidential contracts [P99]."
)
