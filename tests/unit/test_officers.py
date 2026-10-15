"""Unit tests for deterministic executive officer parser (PRD FR-1.1)."""

import pytest
from kgrag.extract.officers import parse_officer_text


def test_parse_officer_text_success():
    sample_text = """
    Item 10. Directors, Executive Officers and Corporate Governance
    The following table sets forth information regarding our executive officers:
    Jensen Huang, President and Chief Executive Officer
    Colette M. Kress, Executive Vice President and Chief Financial Officer
    Debora Shoquist, Executive Vice President, Operations
    """
    filer = "NVIDIA Corporation"
    chunk_id = "test_chunk_officers_001"

    observations = parse_officer_text(chunk_id, sample_text, filer)
    assert len(observations) >= 2

    # Check Jensen Huang
    jensen_obs = next((o for o in observations if "Jensen Huang" in o.head_surface), None)
    assert jensen_obs is not None
    assert jensen_obs.head_type == "Person"
    assert jensen_obs.relation_type == "OFFICER_OF"
    assert jensen_obs.tail_surface == filer
    assert jensen_obs.tail_type == "Company"
    assert "Chief Executive Officer" in jensen_obs.role or "President" in jensen_obs.role
    assert jensen_obs.extraction_method == "parser"

    # Check Colette Kress
    colette_obs = next((o for o in observations if "Colette M. Kress" in o.head_surface), None)
    assert colette_obs is not None
    assert colette_obs.head_type == "Person"
    assert "Chief Financial Officer" in colette_obs.role or "Vice President" in colette_obs.role


def test_parse_officer_text_no_officer_keywords():
    text = "We sell graphics cards and AI accelerators through distributor networks."
    obs = parse_officer_text("chunk_01", text, "NVIDIA Corporation")
    assert obs == []


def test_parse_officer_text_filters_noise_and_headers():
    text = """
    Executive Officers of the Registrant:
    Table of Contents
    Note 1 to Consolidated Financial Statements
    """
    obs = parse_officer_text("chunk_02", text, "Company ABC")
    assert len(obs) == 0
