"""Chunk pre-filter using relation cues and gazetteer mentions (PRD §5.7)."""

import logging
import re
from typing import Any

from kgrag.config import get_prefilter_config

logger = logging.getLogger(__name__)


class ChunkPreFilter:
    """Pre-filters chunks before invoking expensive LLM extraction to conserve compute budget."""

    def __init__(self, config: dict[str, Any] | None = None):
        cfg = config or get_prefilter_config()
        self.cues: list[str] = cfg.get("relation_cues", [])
        self.cue_pattern = re.compile(
            r"\b(" + "|".join(re.escape(cue) for cue in self.cues) + r")",
            re.IGNORECASE,
        )

        gazetteer_cfg = cfg.get("gazetteer", {})
        self.min_entity_mentions = gazetteer_cfg.get("min_entity_mentions", 2)

        # Build alias map
        self.entity_aliases: set[str] = set()
        for ent in gazetteer_cfg.get("seed_entities", []):
            name = ent.get("name")
            if name:
                self.entity_aliases.add(name.lower())
            for alias in ent.get("aliases", []):
                self.entity_aliases.add(alias.lower())

    def add_gazetteer_names(self, names: list[str]) -> None:
        """Dynamically expand gazetteer with Exhibit 21 or discovered entity names."""
        for n in names:
            clean = n.strip().lower()
            if len(clean) >= 3:
                self.entity_aliases.add(clean)

    def should_extract(self, chunk_text: str) -> tuple[bool, str]:
        """Determine if a chunk should be sent to the LLM for structured extraction.

        Condition A: Contains a relation cue word.
        Condition B: Mentions at least 2 distinct entities from the gazetteer.
        """
        if not chunk_text:
            return False, "empty_text"

        # Check Condition A: Relation cue match
        cue_match = self.cue_pattern.search(chunk_text)
        if cue_match:
            return True, f"relation_cue:{cue_match.group(0).lower()}"

        # Check Condition B: Gazetteer entities count
        lowered_text = chunk_text.lower()
        matched_entities = set()
        for alias in self.entity_aliases:
            if re.search(rf"\b{re.escape(alias)}\b", lowered_text):
                matched_entities.add(alias)
                if len(matched_entities) >= self.min_entity_mentions:
                    return True, f"gazetteer_count:{len(matched_entities)}"

        return False, "filtered_no_cue_or_gazetteer"
