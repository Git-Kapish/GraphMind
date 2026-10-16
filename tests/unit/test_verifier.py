"""Unit tests for evidence quote verifier and self-reference resolution (PRD FR-1.3, FR-1.4)."""

from kgrag.extract.verifier import resolve_self_reference, verify_evidence_quote


def test_verify_evidence_quote_exact():
    text = "Taiwan Semiconductor Manufacturing Company (TSMC) manufactures our advanced microprocessors in Taiwan."
    quote = "Taiwan Semiconductor Manufacturing Company (TSMC) manufactures our advanced microprocessors"

    verified, score = verify_evidence_quote(quote, text)
    assert verified is True
    assert score == 1.0


def test_verify_evidence_quote_fuzzy():
    text = "We rely on Taiwan Semiconductor  Manufacturing   Company to fabricate all of our chips."
    # Minor whitespace / casing difference
    quote = "we rely on Taiwan Semiconductor Manufacturing Company to fabricate all of our chips"

    verified, score = verify_evidence_quote(quote, text, threshold=0.85)
    assert verified is True
    assert score >= 0.85


def test_verify_evidence_quote_hallucination_rejected():
    text = "NVIDIA develops graphics processing units and data center solutions."
    quote = "Intel supplies 90 percent of NVIDIA motherboard components."

    verified, score = verify_evidence_quote(quote, text, threshold=0.85)
    assert verified is False
    assert score < 0.60


def test_verify_evidence_quote_empty():
    text = "Some filing text here."
    verified, score = verify_evidence_quote("", text)
    assert verified is False
    assert score == 0.0

    verified, score = verify_evidence_quote("Some text", "")
    assert verified is False
    assert score == 0.0


def test_resolve_self_reference():
    filer = "Advanced Micro Devices, Inc."

    assert resolve_self_reference("the company", filer) == filer
    assert resolve_self_reference("The Company", filer) == filer
    assert resolve_self_reference("We", filer) == filer
    assert resolve_self_reference("our", filer) == filer
    assert resolve_self_reference("the Registrant", filer) == filer
    assert resolve_self_reference("AMD", filer) == "AMD"
    assert resolve_self_reference("Intel Corporation", filer) == "Intel Corporation"


def test_resolve_self_reference_discards_vague_pronouns():
    filer = "NVIDIA Corporation"

    assert resolve_self_reference("they", filer) is None
    assert resolve_self_reference("it", filer) is None
    assert resolve_self_reference("he", filer) is None
    assert resolve_self_reference("she", filer) is None
    assert resolve_self_reference("this", filer) is None
    assert resolve_self_reference("these", filer) is None
    assert resolve_self_reference("none", filer) is None
    assert resolve_self_reference("", filer) is None
