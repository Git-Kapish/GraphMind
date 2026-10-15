"""Deterministic Exhibit 21 Subsidiary Parser (PRD FR-1.1, FR-1.3 rule 11)."""

import hashlib
import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ParserObservation(BaseModel):
    observation_id: str
    chunk_id: str
    extraction_method: str = "parser"
    head_surface: str
    head_type: str
    relation_type: str
    tail_surface: str
    tail_type: str
    evidence_quote: str
    evidence_verified: bool = True
    model_confidence: float = 1.0
    role: str | None = None
    year: int | None = None
    validation_result: dict[str, Any] = {"status": "valid", "parser": "exhibit21"}


def parse_exhibit21_subsidiaries(
    parent_company: str,
    accession: str,
    subsidiaries: list[dict[str, str]],
) -> list[ParserObservation]:
    """Deterministically generate SUBSIDIARY_OF and OPERATES_IN observations from Exhibit 21."""
    observations: list[ParserObservation] = []

    for idx, sub in enumerate(subsidiaries):
        sub_name = sub.get("name", "").strip()
        jurisdiction = sub.get("jurisdiction", "").strip()
        if not sub_name:
            continue

        evidence = (
            f"Subsidiary: {sub_name} | Jurisdiction: {jurisdiction} | Parent: {parent_company}"
        )
        obs_seed = f"{accession}:ex21:{idx}:{sub_name}"
        obs_id = hashlib.sha256(obs_seed.encode("utf-8")).hexdigest()[:16]

        # 1. SUBSIDIARY_OF: sub_name -> parent_company
        observations.append(
            ParserObservation(
                observation_id=f"obs_sub_{obs_id}",
                chunk_id=f"{accession}:exhibit21:0000",
                head_surface=sub_name,
                head_type="Company",
                relation_type="SUBSIDIARY_OF",
                tail_surface=parent_company,
                tail_type="Company",
                evidence_quote=evidence,
            )
        )

        # 2. OPERATES_IN: sub_name -> jurisdiction (if valid jurisdiction)
        if jurisdiction and jurisdiction.lower() not in ["unknown", "none", "nan", ""]:
            jur_id = hashlib.sha256(f"{obs_seed}:jur".encode()).hexdigest()[:16]
            observations.append(
                ParserObservation(
                    observation_id=f"obs_jur_{jur_id}",
                    chunk_id=f"{accession}:exhibit21:0000",
                    head_surface=sub_name,
                    head_type="Company",
                    relation_type="OPERATES_IN",
                    tail_surface=jurisdiction,
                    tail_type="Location",
                    evidence_quote=evidence,
                )
            )

    return observations
