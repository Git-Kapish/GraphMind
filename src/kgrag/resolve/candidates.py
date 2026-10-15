"""Entity candidate generator and similarity matching (PRD §8, Milestone M3)."""

from dataclasses import dataclass
import numpy as np

from kgrag.resolve.normalizer import (
    extract_char_ngrams,
    normalize_company_name,
    tokenize_name,
)


@dataclass
class MatchCandidate:
    canonical_id: str
    canonical_name: str
    score: float
    method: str  # 'exact_match', 'known_alias', 'token_jaccard', 'embedding_cosine'


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity index between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return float(intersection) / float(union) if union > 0 else 0.0


def token_similarity(name_a: str, name_b: str) -> float:
    """Compute combined word and character 3-gram similarity between two entity names."""
    words_a = tokenize_name(name_a)
    words_b = tokenize_name(name_b)
    word_sim = jaccard_similarity(words_a, words_b)

    ngrams_a = extract_char_ngrams(name_a, n=3)
    ngrams_b = extract_char_ngrams(name_b, n=3)
    ngram_sim = jaccard_similarity(ngrams_a, ngrams_b)

    # Weighted combination: 60% word tokens, 40% subword n-grams
    return 0.6 * word_sim + 0.4 * ngram_sim


def cosine_similarity(vec_a: list[float] | np.ndarray, vec_b: list[float] | np.ndarray) -> float:
    """Compute cosine similarity between two dense embedding vectors."""
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def find_best_candidate(
    surface_name: str,
    entity_type: str,
    existing_entities: list[dict],
    review_band_lower: float = 0.70,
    embedding_threshold: float = 0.85,
    query_embedding: list[float] | None = None,
) -> MatchCandidate | None:
    """Find best matching canonical entity candidate across exact, alias, token, and embedding methods."""
    if not surface_name or not existing_entities:
        return None

    norm_surface = (
        normalize_company_name(surface_name) if entity_type == "Company" else surface_name.strip()
    )
    lowered_surface = norm_surface.lower()

    # 1. Exact match on canonical_name or existing aliases
    for ent in existing_entities:
        if ent.get("type") != entity_type:
            continue
        canon_name = ent.get("canonical_name", "")
        norm_canon = (
            normalize_company_name(canon_name) if entity_type == "Company" else canon_name.strip()
        )
        if canon_name.lower() == lowered_surface or norm_canon.lower() == lowered_surface:
            return MatchCandidate(
                canonical_id=ent["entity_id"],
                canonical_name=canon_name,
                score=1.0,
                method="exact_match",
            )
        for alias in ent.get("aliases", []):
            norm_alias = (
                normalize_company_name(alias) if entity_type == "Company" else alias.strip()
            )
            if alias.lower() == lowered_surface or norm_alias.lower() == lowered_surface:
                return MatchCandidate(
                    canonical_id=ent["entity_id"],
                    canonical_name=canon_name,
                    score=1.0,
                    method="alias_match",
                )

    # 2. Token / Jaccard similarity match
    best_token_cand: MatchCandidate | None = None
    best_token_score = 0.0

    for ent in existing_entities:
        if ent.get("type") != entity_type:
            continue
        canon_name = ent.get("canonical_name", "")
        norm_canon = (
            normalize_company_name(canon_name) if entity_type == "Company" else canon_name.strip()
        )
        score = token_similarity(norm_surface, norm_canon)
        if score > best_token_score:
            best_token_score = score
            best_token_cand = MatchCandidate(
                canonical_id=ent["entity_id"],
                canonical_name=canon_name,
                score=round(score, 4),
                method="token_jaccard",
            )

    if best_token_cand and best_token_cand.score >= embedding_threshold:
        return best_token_cand

    # 3. Embedding cosine similarity (if query embedding provided)
    best_emb_cand: MatchCandidate | None = None
    best_emb_score = 0.0

    if query_embedding:
        for ent in existing_entities:
            if ent.get("type") != entity_type:
                continue
            ent_emb = ent.get("name_embedding")
            if not ent_emb:
                continue
            cos_score = cosine_similarity(query_embedding, ent_emb)
            if cos_score > best_emb_score:
                best_emb_score = cos_score
                best_emb_cand = MatchCandidate(
                    canonical_id=ent["entity_id"],
                    canonical_name=ent.get("canonical_name", ""),
                    score=round(cos_score, 4),
                    method="embedding_cosine",
                )

    # Determine highest-scoring candidate between token and embedding
    candidates = [c for c in [best_token_cand, best_emb_cand] if c is not None]
    if not candidates:
        return None

    top_cand = max(candidates, key=lambda c: c.score)
    if top_cand.score >= review_band_lower:
        return top_cand

    return None
