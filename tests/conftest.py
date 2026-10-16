"""Pytest configuration and session fixtures for GraphMind unit tests.

Ensures minimal test fixtures exist in PostgreSQL and Neo4j when running
in fresh CI environments or local container instances without pre-loaded data.
"""

import logging

import pytest

logger = logging.getLogger(__name__)

MOCK_EMBEDDING_2048 = [0.0] * 2048
MOCK_EMBEDDING_2048[0] = 1.0


@pytest.fixture(scope="session", autouse=True)
def ensure_test_database_seeded():
    """Seed minimal test fixtures into PostgreSQL and Neo4j (idempotent for CI & local test runs)."""
    # 1. Ensure PostgreSQL test fixtures exist
    try:
        from kgrag.db.postgres import get_connection

        with get_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                # Insert test documents
                docs = [
                    (
                        "doc_test_nvda",
                        "NVIDIA Corporation",
                        "NVDA",
                        "0001045810",
                        "10-K",
                        2024,
                        "2024-02-21",
                        "0001045810-24-000029",
                        "https://sec.gov",
                        "hash_nvda",
                    ),
                    (
                        "doc_test_amd",
                        "Advanced Micro Devices, Inc.",
                        "AMD",
                        "0000002488",
                        "10-K",
                        2024,
                        "2024-02-21",
                        "0000002488-24-000012",
                        "https://sec.gov",
                        "hash_amd",
                    ),
                    (
                        "doc_test_msft",
                        "Microsoft Corporation",
                        "MSFT",
                        "0000789019",
                        "10-K",
                        2024,
                        "2024-02-21",
                        "0000789019-24-000015",
                        "https://sec.gov",
                        "hash_msft",
                    ),
                    (
                        "doc_test_broadcom",
                        "Broadcom Inc.",
                        "AVGO",
                        "0001730168",
                        "10-K",
                        2024,
                        "2024-02-21",
                        "0001730168-24-000018",
                        "https://sec.gov",
                        "hash_avgo",
                    ),
                ]
                for d in docs:
                    cur.execute(
                        """
                        INSERT INTO documents (doc_id, company, ticker, cik, form_type, fiscal_year, filing_date, accession, source_url, sha256)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (doc_id) DO NOTHING;
                        """,
                        d,
                    )

                # Insert test entities
                entities = [
                    (
                        "ent_4e47c272d2b7",
                        "Company",
                        "nvidia",
                        ["Nvidia", "NVIDIA CORP", "NVIDIA Corporation", "NVDA"],
                    ),
                    (
                        "ent_99ee45010f6a",
                        "Company",
                        "amd",
                        ["AMD", "Advanced Micro Devices", "Advanced Micro Devices, Inc."],
                    ),
                    (
                        "ent_bfd5f0618c63",
                        "Company",
                        "microsoft",
                        ["MICROSOFT CORP", "Microsoft", "MSFT"],
                    ),
                    (
                        "ent_1c45946c94de",
                        "Company",
                        "broadcom",
                        ["Broadcom Inc.", "Broadcom Corporation", "Broadcom", "AVGO"],
                    ),
                    (
                        "ent_jensen_huang",
                        "Person",
                        "jensen huang",
                        ["Jensen Huang"],
                    ),
                    (
                        "ent_mellanox",
                        "Company",
                        "mellanox",
                        ["Mellanox Technologies", "Mellanox"],
                    ),
                    (
                        "ent_vmware",
                        "Company",
                        "vmware",
                        ["VMware", "VMware LLC"],
                    ),
                    (
                        "ent_tsmc",
                        "Company",
                        "taiwan semiconductor manufacturing company",
                        ["Taiwan Semiconductor Manufacturing Company Limited", "TSMC"],
                    ),
                ]
                from kgrag.llm.client import generate_deterministic_embedding

                for eid, etype, cname, aliases in entities:
                    emb = generate_deterministic_embedding(cname, dim=2048)
                    cur.execute(
                        """
                        INSERT INTO entities (entity_id, type, canonical_name, aliases, name_embedding, embedding_model)
                        VALUES (%s, %s, %s, %s, %s::vector, 'nvidia/nemotron-3-embed-1b:free')
                        ON CONFLICT (entity_id) DO UPDATE
                        SET aliases = EXCLUDED.aliases,
                            canonical_name = EXCLUDED.canonical_name,
                            name_embedding = EXCLUDED.name_embedding;
                        """,
                        (eid, etype, cname, aliases, str(emb)),
                    )

                # Insert test chunks (at least 3 chunks with embeddings for retrieve_vector top_k=3)
                chunks = [
                    (
                        "chk_test_nvda_001",
                        "doc_test_nvda",
                        "Item 1. Business",
                        "Item 1",
                        "NVIDIA Corporation designs graphics processing units and accelerated computing platforms. Jensen Huang is the Chief Executive Officer.",
                        30,
                        0,
                        150,
                        ["ent_4e47c272d2b7", "ent_jensen_huang"],
                    ),
                    (
                        "chk_test_amd_001",
                        "doc_test_amd",
                        "Item 1. Business",
                        "Item 1",
                        "Advanced Micro Devices provides high-performance computing, graphics, and visualization technologies.",
                        25,
                        0,
                        120,
                        ["ent_99ee45010f6a"],
                    ),
                    (
                        "chk_test_msft_001",
                        "doc_test_msft",
                        "Item 1. Business",
                        "Item 1",
                        "Microsoft Corporation develops and supports software, services, devices, and cloud computing solutions.",
                        25,
                        0,
                        120,
                        ["ent_bfd5f0618c63"],
                    ),
                ]
                for cid, did, sec, item, txt, tc, cs, ce, eids in chunks:
                    chunk_emb = generate_deterministic_embedding(txt, dim=2048)
                    cur.execute(
                        """
                        INSERT INTO chunks (chunk_id, doc_id, section_path, item, text, token_count, char_start, char_end, entity_ids, embedding, embedding_model)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, 'nvidia/nemotron-3-embed-1b:free')
                        ON CONFLICT (chunk_id) DO UPDATE
                        SET embedding = EXCLUDED.embedding;
                        """,
                        (cid, did, sec, item, txt, tc, cs, ce, eids, str(chunk_emb)),
                    )

                # Insert extraction observations
                obs = [
                    (
                        "obs_nvda_competes_amd",
                        "chk_test_nvda_001",
                        "llm",
                        "NVIDIA",
                        "Company",
                        "COMPETES_WITH",
                        "AMD",
                        "Company",
                        "ent_4e47c272d2b7",
                        "ent_99ee45010f6a",
                        "resolved",
                        "NVIDIA competes with Advanced Micro Devices (AMD)",
                        True,
                    ),
                    (
                        "obs_jensen_officer_nvda",
                        "chk_test_nvda_001",
                        "llm",
                        "Jensen Huang",
                        "Person",
                        "OFFICER_OF",
                        "NVIDIA",
                        "Company",
                        "ent_jensen_huang",
                        "ent_4e47c272d2b7",
                        "resolved",
                        "Jensen Huang is the Chief Executive Officer.",
                        True,
                    ),
                    (
                        "obs_mellanox_subsidiary",
                        "chk_test_nvda_001",
                        "llm",
                        "Mellanox",
                        "Company",
                        "SUBSIDIARY_OF",
                        "NVIDIA",
                        "Company",
                        "ent_mellanox",
                        "ent_4e47c272d2b7",
                        "resolved",
                        "Mellanox is a subsidiary of NVIDIA.",
                        True,
                    ),
                    (
                        "obs_broadcom_subsidiary",
                        "chk_test_nvda_001",
                        "llm",
                        "Broadcom",
                        "Company",
                        "SUBSIDIARY_OF",
                        "VMware",
                        "Company",
                        "ent_1c45946c94de",
                        "ent_vmware",
                        "resolved",
                        "Broadcom acquired VMware.",
                        True,
                    ),
                    (
                        "obs_amd_subsidiary",
                        "chk_test_amd_001",
                        "llm",
                        "AMD",
                        "Company",
                        "SUBSIDIARY_OF",
                        "Xilinx",
                        "Company",
                        "ent_99ee45010f6a",
                        "ent_vmware",
                        "resolved",
                        "AMD subsidiaries include Xilinx.",
                        True,
                    ),
                ]
                for oid, cid, method, hs, ht, rel, ts, tt, hid, tid, status, quote, verified in obs:
                    cur.execute(
                        """
                        INSERT INTO extraction_observations (observation_id, chunk_id, extraction_method, head_surface, head_type, relation_type, tail_surface, tail_type, head_entity_id, tail_entity_id, resolution_status, evidence_quote, evidence_verified)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (observation_id) DO NOTHING;
                        """,
                        (oid, cid, method, hs, ht, rel, ts, tt, hid, tid, status, quote, verified),
                    )
    except Exception as e:
        logger.warning("PostgreSQL test fixture seeding skipped or failed: %s", e)

    # 2. Ensure Neo4j test fixtures exist
    try:
        from kgrag.db.neo4j import get_session

        with get_session() as session:
            cypher = """
            MERGE (nvda:Entity {entity_id: 'ent_4e47c272d2b7'})
            SET nvda.canonical_name = 'nvidia', nvda.type = 'Company', nvda.aliases = ['NVIDIA Corporation', 'NVDA']

            MERGE (amd:Entity {entity_id: 'ent_99ee45010f6a'})
            SET amd.canonical_name = 'amd', amd.type = 'Company', amd.aliases = ['Advanced Micro Devices', 'AMD']

            MERGE (msft:Entity {entity_id: 'ent_bfd5f0618c63'})
            SET msft.canonical_name = 'microsoft', msft.type = 'Company', msft.aliases = ['Microsoft Corporation', 'MSFT']

            MERGE (avgo:Entity {entity_id: 'ent_1c45946c94de'})
            SET avgo.canonical_name = 'broadcom', avgo.type = 'Company', avgo.aliases = ['Broadcom Inc.', 'AVGO']

            MERGE (jensen:Entity {entity_id: 'ent_jensen_huang'})
            SET jensen.canonical_name = 'jensen huang', jensen.type = 'Person', jensen.aliases = ['Jensen Huang']

            MERGE (mellanox:Entity {entity_id: 'ent_mellanox'})
            SET mellanox.canonical_name = 'mellanox', mellanox.type = 'Company', mellanox.aliases = ['Mellanox Technologies']

            MERGE (vmware:Entity {entity_id: 'ent_vmware'})
            SET vmware.canonical_name = 'vmware', vmware.type = 'Company', vmware.aliases = ['VMware']

            MERGE (tsmc:Entity {entity_id: 'ent_tsmc'})
            SET tsmc.canonical_name = 'taiwan semiconductor manufacturing company', tsmc.type = 'Company', tsmc.aliases = ['TSMC']

            MERGE (nvda)-[:COMPETES_WITH {observation_ids: ['obs_nvda_competes_amd'], source_chunks: ['chk_test_nvda_001'], weight: 1.0}]->(amd)
            MERGE (amd)-[:COMPETES_WITH {observation_ids: ['obs_nvda_competes_amd'], source_chunks: ['chk_test_nvda_001'], weight: 1.0}]->(nvda)
            MERGE (nvda)-[:PARTNERS_WITH {observation_ids: ['obs_nvda_msft'], source_chunks: ['chk_test_nvda_001'], weight: 1.0}]->(msft)
            MERGE (msft)-[:PARTNERS_WITH {observation_ids: ['obs_msft_tsmc'], source_chunks: ['chk_test_nvda_001'], weight: 1.0}]->(tsmc)
            MERGE (nvda)-[:PARTNERS_WITH {observation_ids: ['obs_nvda_tsmc'], source_chunks: ['chk_test_nvda_001'], weight: 1.0}]->(tsmc)
            MERGE (jensen)-[:OFFICER_OF {observation_ids: ['obs_jensen_officer_nvda'], source_chunks: ['chk_test_nvda_001'], role: 'Chief Executive Officer', weight: 1.0}]->(nvda)
            MERGE (mellanox)-[:SUBSIDIARY_OF {observation_ids: ['obs_mellanox_subsidiary'], source_chunks: ['chk_test_nvda_001'], weight: 1.0}]->(nvda)
            MERGE (avgo)-[:SUBSIDIARY_OF {observation_ids: ['obs_broadcom_subsidiary'], source_chunks: ['chk_test_nvda_001'], weight: 1.0}]->(vmware)
            MERGE (amd)-[:SUBSIDIARY_OF {observation_ids: ['obs_amd_subsidiary'], source_chunks: ['chk_test_amd_001'], weight: 1.0}]->(vmware)
            """
            session.run(cypher)
    except Exception as e:
        logger.warning("Neo4j test fixture seeding skipped or failed: %s", e)
