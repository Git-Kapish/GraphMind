"""Deterministic Executive Officer Parser (PRD FR-1.1, FR-1.3 rule 11)."""

import hashlib
import logging
import re

from kgrag.extract.exhibit21 import ParserObservation

logger = logging.getLogger(__name__)

# Standard executive title patterns
OFFICER_TITLE_PATTERNS = [
    r"Chief Executive Officer",
    r"Chief Financial Officer",
    r"Chief Operating Officer",
    r"Chief Technology Officer",
    r"Chief Legal Officer",
    r"President",
    r"Executive Vice President",
    r"Senior Vice President",
    r"Vice President",
    r"General Counsel",
    r"Corporate Controller",
]

TITLE_REGEX = re.compile(
    r"\b(" + "|".join(OFFICER_TITLE_PATTERNS) + r")\b",
    re.IGNORECASE,
)


def parse_officer_text(
    chunk_id: str,
    text: str,
    filer_company: str,
) -> list[ParserObservation]:
    """Parse executive officer disclosures deterministically without an LLM."""
    observations: list[ParserObservation] = []

    # Check if chunk discusses executive officers
    if not re.search(r"executive officer|officer of the company|named executive", text, re.I):
        return []

    lines = text.split("\n")
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 5 or len(line_clean) > 250:
            continue

        # Look for patterns like: "Jensen Huang, President and Chief Executive Officer"
        # or "Colette M. Kress ... Chief Financial Officer"
        match = TITLE_REGEX.search(line_clean)
        if match:
            role = match.group(0).strip()
            # The person name typically precedes the title (or is separated by comma/dash)
            parts = re.split(r"[,–—\-|]", line_clean[: match.end() + 20])
            potential_name = parts[0].strip()

            # Clean name from age or numbers e.g. "Jensen Huang, 61" -> "Jensen Huang"
            name_match = re.match(
                r"^([A-Z][a-zA-Z\.\'\-]+(?:\s+[A-Z][a-zA-Z\.\'\-]+){1,3})", potential_name
            )
            if name_match:
                person_name = name_match.group(1).strip()
                # Skip if person_name contains non-name keywords
                if not re.search(
                    r"\b(item|table|page|note|the|our|company|section|inc|corp)\b",
                    person_name,
                    re.I,
                ):
                    obs_seed = f"{chunk_id}:officer:{idx}:{person_name}"
                    obs_id = hashlib.sha256(obs_seed.encode("utf-8")).hexdigest()[:16]

                    observations.append(
                        ParserObservation(
                            observation_id=f"obs_off_{obs_id}",
                            chunk_id=chunk_id,
                            extraction_method="parser",
                            head_surface=person_name,
                            head_type="Person",
                            relation_type="OFFICER_OF",
                            tail_surface=filer_company,
                            tail_type="Company",
                            evidence_quote=line_clean,
                            role=role,
                            validation_result={"status": "valid", "parser": "officer_table"},
                        )
                    )

    return observations
