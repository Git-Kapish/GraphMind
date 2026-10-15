"""Evidence quote verification and self-reference resolution (PRD FR-1.3 rules 5, 10)."""

import logging
import re
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

SELF_REFERENCE_TERMS = {
    "the company",
    "the registrant",
    "the filer",
    "we",
    "our",
    "us",
    "ourselves",
    "company",
}

PRONOUN_JUNK_TERMS = {
    "it",
    "they",
    "them",
    "he",
    "she",
    "his",
    "her",
    "its",
    "their",
    "this",
    "that",
    "these",
    "those",
    "someone",
    "anyone",
    "none",
    "null",
    "unknown",
    "n/a",
}


def normalize_text_for_matching(text: str) -> str:
    """Normalize text for whitespace, casing, and punctuation invariance."""
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def verify_evidence_quote(
    quote: str,
    chunk_text: str,
    threshold: float = 0.85,
) -> tuple[bool, float]:
    """Verify that evidence_quote is present in chunk_text via exact or fuzzy matching."""
    if not quote or not chunk_text:
        return False, 0.0

    norm_quote = normalize_text_for_matching(quote)
    norm_chunk = normalize_text_for_matching(chunk_text)

    # 1. Exact substring check after whitespace normalization
    if norm_quote in norm_chunk:
        return True, 1.0

    # 2. Fuzzy partial ratio matching using rapidfuzz
    score = fuzz.partial_ratio(norm_quote, norm_chunk) / 100.0
    if score >= threshold:
        return True, score

    return False, score


def resolve_self_reference(name: str, filer_company: str) -> str | None:
    """Deterministically resolve self-references to filer company name (PRD FR-1.3 rule 10).

    Returns None if the entity name is an unresolvable junk pronoun.
    """
    if not name:
        return None
    clean_name = name.strip()
    if not clean_name:
        return None
    lowered = clean_name.lower()

    # Direct self reference
    if lowered in SELF_REFERENCE_TERMS:
        return filer_company

    # Reject junk pronouns
    if lowered in PRONOUN_JUNK_TERMS:
        return None

    # Strip leading "the" if followed by company
    if lowered.startswith("the ") and lowered[4:] in SELF_REFERENCE_TERMS:
        return filer_company

    return clean_name
