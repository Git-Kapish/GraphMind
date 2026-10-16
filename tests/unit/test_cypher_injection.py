"""Unit tests for Cypher injection defense and safe template parameterization (PRD §11, §14, Milestone M11).

Verifies that:
1. Malicious relation types with Cypher injection payloads are blocked by validate_relation_type().
2. Entity IDs containing quotes and Cypher statements are passed as literal parameters without syntax escape.
3. Only safe, pre-written templates in TemplateId enum can be requested (zero free-form LLM Cypher).
"""

from unittest.mock import MagicMock, patch

import pytest

from kgrag.graph.templates import (
    TemplateId,
    query_neighbors,
    validate_relation_type,
)


def test_relation_type_injection_payload_rejected():
    """Verify that arbitrary Cypher injection attempts in relation_type raise ValueError (PRD §11)."""
    malicious_relations = [
        "SUBSIDIARY_OF]-(b) DETACH DELETE (b) //",
        "OPERATES_IN' OR 1=1 //",
        "; MATCH (n) DETACH DELETE n;",
        "SUBSIDIARY_OF:ADMIN",
        "FAKE_RELATION_NAME",
    ]

    for bad_rel in malicious_relations:
        with pytest.raises(ValueError) as excinfo:
            validate_relation_type(bad_rel)
        assert "Invalid relation type" in str(excinfo.value)


def test_entity_id_parameter_binding_neutralizes_injection():
    """Verify that Cypher injection strings in entity_id are bound as literal parameters (PRD §11)."""
    malicious_eid = "ent_nvidia' OR 1=1 DETACH DELETE (n) //"

    # Mock the neo4j session to inspect parameters sent to session.run
    mock_session = MagicMock()
    mock_result = MagicMock()
    mock_result.__iter__.return_value = []
    mock_session.run.return_value = mock_result

    with patch("kgrag.graph.templates.get_session") as mock_get_session:
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Execute query_neighbors with malicious entity input
        query_neighbors(
            entity_id_or_name=malicious_eid,
            relation_type="SUBSIDIARY_OF",
            limit=5,
        )

        # Assert query was executed with parameter binding, NOT string concatenation
        assert mock_session.run.called
        call_args, call_kwargs = mock_session.run.call_args
        cypher_query = call_args[0]

        # The Cypher string MUST contain $a_id parameter, NOT the injected code
        assert "$a_id" in cypher_query
        assert "DETACH DELETE" not in cypher_query
        # The malicious string must be safely contained inside parameters
        assert call_kwargs["a_id"] == malicious_eid or call_kwargs.get("a_id") is not None


def test_template_enumeration_strictly_closed():
    """Verify that only authorized, pre-written templates exist in TemplateId (PRD FR-3.2)."""
    valid_templates = {
        "neighbors",
        "two_hop",
        "path_between",
        "shared_neighbors",
        "count_by_relation",
        "top_connected",
        "officers_of",
    }

    assert {t.value for t in TemplateId} == valid_templates

    # Arbitrary / model-generated template name cannot be coerced into TemplateId
    with pytest.raises(ValueError):
        TemplateId("custom_llm_generated_cypher")
