"""Hardened Entity Resolution with Candidate Matching, Review Queue, and Merge History (PRD §8, Milestone M3)."""

import hashlib
import logging
import time
from typing import Any

from kgrag.config import get_settings
from kgrag.db.postgres import get_connection
from kgrag.llm.client import get_llm_client
from kgrag.resolve.candidates import find_best_candidate
from kgrag.resolve.normalizer import clean_whitespace, normalize_company_name

logger = logging.getLogger(__name__)


def generate_entity_id(canonical_name: str, entity_type: str) -> str:
    """Generate deterministic canonical entity ID."""
    seed = f"{entity_type.lower()}:{canonical_name.lower().strip()}"
    return f"ent_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def normalize_name(raw_name: str, entity_type: str = "Company") -> tuple[str, str]:
    """Normalize surface name and generate canonical name and deterministic entity_id."""
    if not raw_name:
        return "Unknown", "ent_unknown"

    if entity_type == "Company":
        canonical = normalize_company_name(raw_name)
    else:
        canonical = clean_whitespace(raw_name)

    entity_id = generate_entity_id(canonical, entity_type)
    return canonical, entity_id


def embed_unembedded_entities(batch_size: int = 32) -> int:
    """Generate 768-d vector embeddings for canonical entities in PostgreSQL lacking embeddings."""
    llm = get_llm_client()
    settings = get_settings()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT entity_id, canonical_name
                FROM entities
                WHERE name_embedding IS NULL
                ORDER BY entity_id;
                """
            )
            rows = cur.fetchall()

    if not rows:
        logger.info("All entities already have embeddings.")
        return 0

    total_entities = len(rows)
    logger.info("Generating embeddings for %d entities in batches of %d...", total_entities, batch_size)
    updated = 0

    update_sql = """
    UPDATE entities
    SET name_embedding = %(embedding)s::vector,
        embedding_model = %(model)s
    WHERE entity_id = %(entity_id)s;
    """

    for i in range(0, total_entities, batch_size):
        batch = rows[i : i + batch_size]
        texts = [r["canonical_name"] for r in batch]
        embeddings = llm.embed(texts)

        with get_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                for r, emb in zip(batch, embeddings):
                    cur.execute(
                        update_sql,
                        {
                            "entity_id": r["entity_id"],
                            "embedding": str(emb),
                            "model": settings.embedding.model,
                        },
                    )
        updated += len(batch)

    logger.info("Embedded %d entities.", updated)
    return updated


def resolve_all_observations(force: bool = False) -> dict[str, int]:
    """Execute hardened entity resolution across observations with merge history auditing."""
    settings = get_settings()
    exact_thresh = settings.resolution.exact_match_threshold
    sim_thresh = settings.resolution.embedding_similarity_threshold
    review_lower = settings.resolution.review_band_lower
    review_upper = settings.resolution.review_band_upper

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Load existing canonical entities
            cur.execute("SELECT entity_id, type, canonical_name, aliases FROM entities;")
            existing_entities = cur.fetchall()

            # 2. Fetch observations
            if force:
                cur.execute(
                    """
                    SELECT observation_id, head_surface, head_type, tail_surface, tail_type
                    FROM extraction_observations;
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT observation_id, head_surface, head_type, tail_surface, tail_type
                    FROM extraction_observations
                    WHERE resolution_status = 'pending'
                       OR head_entity_id IS NULL
                       OR tail_entity_id IS NULL;
                    """
                )
            pending_rows = cur.fetchall()

    if not pending_rows:
        logger.info("No observations to resolve.")
        return {"observations_resolved": 0, "entities_created": 0, "merges_recorded": 0}

    logger.info("Hardened resolution on %d observations (force=%s)...", len(pending_rows), force)

    entities_by_id: dict[str, dict[str, Any]] = {e["entity_id"]: dict(e) for e in existing_entities}
    merges_to_insert: list[dict[str, Any]] = []
    obs_updates: list[tuple[str, str, str, str]] = []  # (head_id, tail_id, status, obs_id)
    new_entities: dict[str, dict[str, Any]] = {}
    updated_aliases: dict[str, set[str]] = {}

    def resolve_endpoint(surface: str, ent_type: str) -> tuple[str, str, str | None, float]:
        """Resolve a single entity endpoint surface to canonical ID, status, and merge method."""
        canon_name, raw_id = normalize_name(surface, ent_type)

        # Check existing entities in memory
        active_list = list(entities_by_id.values()) + list(new_entities.values())
        match = find_best_candidate(
            surface_name=surface,
            entity_type=ent_type,
            existing_entities=active_list,
            review_band_lower=review_lower,
            embedding_threshold=sim_thresh,
        )

        if match:
            target_id = match.canonical_id
            if match.score >= sim_thresh:
                # Auto-merge into existing canonical entity
                if target_id != raw_id:
                    merges_to_insert.append(
                        {
                            "source_entity_id": raw_id,
                            "canonical_entity_id": target_id,
                            "decision": "auto_merged",
                            "method": match.method,
                            "score": match.score,
                            "reviewer_note": f"Auto-merged '{surface}' -> '{match.canonical_name}'",
                        }
                    )
                    # Accumulate surface form as alias
                    updated_aliases.setdefault(target_id, set()).add(surface)
                return target_id, "resolved", match.method, match.score
            elif review_lower <= match.score < review_upper:
                # Ambiguous: flag for review queue
                merges_to_insert.append(
                    {
                        "source_entity_id": raw_id,
                        "canonical_entity_id": target_id,
                        "decision": "needs_review",
                        "method": match.method,
                        "score": match.score,
                        "reviewer_note": f"Flagged in review band: '{surface}' vs '{match.canonical_name}'",
                    }
                )
                return target_id, "needs_review", match.method, match.score

        # No match above threshold: create distinct entity
        if raw_id not in entities_by_id and raw_id not in new_entities:
            new_entities[raw_id] = {
                "entity_id": raw_id,
                "type": ent_type,
                "canonical_name": canon_name,
                "aliases": [surface],
            }
        return raw_id, "resolved", "distinct_new", 1.0

    for r in pending_rows:
        obs_id = r["observation_id"]
        head_id, head_status, _, _ = resolve_endpoint(r["head_surface"], r["head_type"])
        tail_id, tail_status, _, _ = resolve_endpoint(r["tail_surface"], r["tail_type"])

        final_status = (
            "needs_review"
            if (head_status == "needs_review" or tail_status == "needs_review")
            else "resolved"
        )
        obs_updates.append((head_id, tail_id, final_status, obs_id))

    # Persist new entities and merge records to PostgreSQL
    upsert_entity_sql = """
    INSERT INTO entities (entity_id, type, canonical_name, aliases)
    VALUES (%(entity_id)s, %(type)s, %(canonical_name)s, %(aliases)s)
    ON CONFLICT (entity_id) DO UPDATE SET
        canonical_name = EXCLUDED.canonical_name,
        aliases = ARRAY(SELECT DISTINCT unnest(entities.aliases || EXCLUDED.aliases));
    """

    merge_history_sql = """
    INSERT INTO entity_merge_history (source_entity_id, canonical_entity_id, decision, method, score, reviewer_note)
    VALUES (%(source_entity_id)s, %(canonical_entity_id)s, %(decision)s, %(method)s, %(score)s, %(reviewer_note)s);
    """

    update_obs_sql = """
    UPDATE extraction_observations
    SET head_entity_id = %s,
        tail_entity_id = %s,
        resolution_status = %s
    WHERE observation_id = %s;
    """

    with get_connection(autocommit=True) as conn:
        with conn.cursor() as cur:
            # 1. Insert new entities
            for ent in new_entities.values():
                cur.execute(upsert_entity_sql, ent)

            # 2. Insert merge history audit records
            for m in merges_to_insert:
                cur.execute(merge_history_sql, m)

            # 3. Update observation links
            cur.executemany(update_obs_sql, obs_updates)

            # 4. Update aliases for existing entities
            update_alias_sql = """
            UPDATE entities
            SET aliases = ARRAY(SELECT DISTINCT unnest(aliases || %(new_aliases)s::text[]))
            WHERE entity_id = %(entity_id)s;
            """
            for eid, aliases in updated_aliases.items():
                cur.execute(update_alias_sql, {"entity_id": eid, "new_aliases": list(aliases)})

    logger.info(
        "Hardened resolution complete: %d observations linked, %d new entities created, %d merge decisions recorded.",
        len(obs_updates),
        len(new_entities),
        len(merges_to_insert),
    )

    return {
        "observations_resolved": len(obs_updates),
        "entities_created": len(new_entities),
        "merges_recorded": len(merges_to_insert),
    }


def get_merge_history(limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve audit trail of recent entity resolution decisions."""
    sql = """
    SELECT id, source_entity_id, canonical_entity_id, decision, method, score, reviewer_note, created_at
    FROM entity_merge_history
    ORDER BY id DESC
    LIMIT %(limit)s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"limit": limit})
            return cur.fetchall()


def get_review_queue() -> list[dict[str, Any]]:
    """Retrieve ambiguous entity pairs awaiting human or model review."""
    sql = """
    SELECT id, source_entity_id, canonical_entity_id, decision, score, method, reviewer_note, created_at
    FROM entity_merge_history
    WHERE decision = 'needs_review'
    ORDER BY id DESC;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Entity Resolution CLI (PRD §8, Milestone M3)")
    parser.add_argument("--force", action="store_true", help="Force re-resolution across all observations")
    parser.add_argument("--no-embed", action="store_true", help="Skip embedding generation for new entities")
    args = parser.parse_args()

    resolve_all_observations(force=args.force)
    if not args.no_embed:
        embed_unembedded_entities()
