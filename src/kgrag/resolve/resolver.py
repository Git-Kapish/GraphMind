"""Entity Resolution and Canonical Identification (PRD §8, Milestone M2.5/M3)."""

import hashlib
import logging
import re
from typing import Any

from kgrag.db.postgres import get_connection

logger = logging.getLogger(__name__)

# Legal and corporate suffix regex
LEGAL_SUFFIX_REGEX = re.compile(
    r"\b(inc|incorporated|corp|corporation|llc|l\.l\.c|ltd|limited|co|company|holdings|plc|s\.a|b\.v|gmbh|opco)\b\.?",
    re.IGNORECASE,
)

# Known canonical enterprise mappings
KNOWN_CANONICAL_ALIASES: dict[str, str] = {
    "tsmc": "Taiwan Semiconductor Manufacturing Company",
    "taiwan semiconductor manufacturing company": "Taiwan Semiconductor Manufacturing Company",
    "taiwan semiconductor manufacturing company limited": "Taiwan Semiconductor Manufacturing Company",
    "taiwan semiconductor manufacturing co., ltd.": "Taiwan Semiconductor Manufacturing Company",
    "taiwan semiconductor": "Taiwan Semiconductor Manufacturing Company",
    "nvidia": "NVIDIA Corporation",
    "nvidia corp": "NVIDIA Corporation",
    "nvidia corporation": "NVIDIA Corporation",
    "amd": "Advanced Micro Devices, Inc.",
    "advanced micro devices": "Advanced Micro Devices, Inc.",
    "advanced micro devices, inc.": "Advanced Micro Devices, Inc.",
    "intel": "Intel Corporation",
    "intel corp": "Intel Corporation",
    "intel corporation": "Intel Corporation",
    "micron": "Micron Technology, Inc.",
    "micron technology": "Micron Technology, Inc.",
    "micron technology, inc.": "Micron Technology, Inc.",
    "microsoft": "Microsoft Corporation",
    "microsoft corp": "Microsoft Corporation",
    "microsoft corporation": "Microsoft Corporation",
    "broadcom": "Broadcom Inc.",
    "broadcom inc": "Broadcom Inc.",
    "broadcom inc.": "Broadcom Inc.",
    "openai": "OpenAI",
    "openai opco": "OpenAI",
    "openai opco, llc": "OpenAI",
    "sanmina": "Sanmina Corporation",
    "sanmina corp": "Sanmina Corporation",
    "sanmina corporation": "Sanmina Corporation",
    "cisco": "Cisco Systems, Inc.",
    "cisco systems": "Cisco Systems, Inc.",
    "cisco systems, inc.": "Cisco Systems, Inc.",
}


def normalize_name(raw_name: str, entity_type: str = "Company") -> tuple[str, str]:
    """Normalize surface name and generate canonical name and deterministic entity_id.

    Returns:
        (canonical_name, entity_id)
    """
    if not raw_name:
        return "Unknown", "ent_unknown"

    clean = raw_name.strip()
    lowered = clean.lower()

    # 1. Check known enterprise aliases
    if entity_type == "Company":
        # Remove trailing parentheticals, e.g. "Taiwan Semiconductor (TSMC)" -> "Taiwan Semiconductor"
        clean_no_paren = re.sub(r"\s*\([^)]*\)$", "", clean).strip()
        lowered_no_paren = clean_no_paren.lower()

        if lowered in KNOWN_CANONICAL_ALIASES:
            canonical = KNOWN_CANONICAL_ALIASES[lowered]
        elif lowered_no_paren in KNOWN_CANONICAL_ALIASES:
            canonical = KNOWN_CANONICAL_ALIASES[lowered_no_paren]
        else:
            # Strip legal suffix for clean canonical matching
            stripped = LEGAL_SUFFIX_REGEX.sub("", clean_no_paren).strip().rstrip(",.-")
            stripped = re.sub(r"\s+", " ", stripped).strip()
            canonical = stripped if len(stripped) >= 2 else clean_no_paren
    elif entity_type == "Person":
        # Remove trailing titles or honorifics, strip whitespace
        canonical = re.sub(r"\s+", " ", clean).strip()
    else:
        # Product, Technology, Market, Location, Regulation
        canonical = re.sub(r"\s+", " ", clean).strip()

    # Generate deterministic entity ID
    seed = f"{entity_type.lower()}:{canonical.lower()}"
    entity_id = f"ent_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"

    return canonical, entity_id


def resolve_all_observations() -> dict[str, int]:
    """Resolve all pending extraction observations, populate entities table, and link IDs."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Fetch unlinked observations
            cur.execute(
                """
                SELECT observation_id, head_surface, head_type, tail_surface, tail_type
                FROM extraction_observations
                WHERE resolution_status = 'pending'
                   OR head_entity_id IS NULL
                   OR tail_entity_id IS NULL;
                """
            )
            rows = cur.fetchall()

    if not rows:
        logger.info("No pending observations to resolve.")
        return {"observations_resolved": 0, "entities_upserted": 0}

    logger.info("Resolving entities for %d observations...", len(rows))

    # Collect entities to upsert
    entities_map: dict[str, dict[str, Any]] = {}
    updates: list[tuple[str, str, str]] = []

    for r in rows:
        obs_id = r["observation_id"]
        head_canon, head_id = normalize_name(r["head_surface"], r["head_type"])
        tail_canon, tail_id = normalize_name(r["tail_surface"], r["tail_type"])

        # Track head entity
        if head_id not in entities_map:
            entities_map[head_id] = {
                "entity_id": head_id,
                "type": r["head_type"],
                "canonical_name": head_canon,
                "aliases": {r["head_surface"]},
            }
        else:
            entities_map[head_id]["aliases"].add(r["head_surface"])

        # Track tail entity
        if tail_id not in entities_map:
            entities_map[tail_id] = {
                "entity_id": tail_id,
                "type": r["tail_type"],
                "canonical_name": tail_canon,
                "aliases": {r["tail_surface"]},
            }
        else:
            entities_map[tail_id]["aliases"].add(r["tail_surface"])

        updates.append((head_id, tail_id, obs_id))

    # Upsert entities into PostgreSQL
    upsert_entity_sql = """
    INSERT INTO entities (entity_id, type, canonical_name, aliases)
    VALUES (%(entity_id)s, %(type)s, %(canonical_name)s, %(aliases)s)
    ON CONFLICT (entity_id) DO UPDATE SET
        canonical_name = EXCLUDED.canonical_name,
        aliases = ARRAY(
            SELECT DISTINCT unnest(entities.aliases || EXCLUDED.aliases)
        );
    """

    update_obs_sql = """
    UPDATE extraction_observations
    SET head_entity_id = %s,
        tail_entity_id = %s,
        resolution_status = 'resolved'
    WHERE observation_id = %s;
    """

    with get_connection(autocommit=True) as conn:
        with conn.cursor() as cur:
            for ent in entities_map.values():
                cur.execute(
                    upsert_entity_sql,
                    {
                        "entity_id": ent["entity_id"],
                        "type": ent["type"],
                        "canonical_name": ent["canonical_name"],
                        "aliases": list(ent["aliases"]),
                    },
                )

            # Batch update observations
            cur.executemany(update_obs_sql, updates)

    logger.info(
        "Entity resolution complete: %d observations linked, %d entities upserted.",
        len(updates),
        len(entities_map),
    )

    return {
        "observations_resolved": len(updates),
        "entities_upserted": len(entities_map),
    }


if __name__ == "__main__":
    resolve_all_observations()
