"""10-K Section and Item Parser with Exhibit 21 support (PRD §5.1, §5.2)."""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from kgrag.config import get_settings
from kgrag.data.sec_fetcher import FilingMetadata

logger = logging.getLogger(__name__)


class SectionContent(BaseModel):
    item: str
    section_name: str
    text: str
    char_count: int
    sha256: str


class ParsedFiling(BaseModel):
    metadata: FilingMetadata
    sections: list[SectionContent] = Field(default_factory=list)
    subsidiaries_count: int = 0
    subsidiaries: list[dict[str, str]] = Field(default_factory=list)


def clean_section_text(text: str) -> str:
    """Normalize whitespace and strip unnecessary boilerplate while preserving table and paragraph structure."""
    if not text:
        return ""
    # Replace multiple blank lines with double newlines
    text = re.sub(r"\r\n|\r", "\n", text)
    # Remove excessive horizontal spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Normalize paragraph breaks
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class SECParser:
    """Extracts Item 1, Item 1A, Item 7, executive officers, and Exhibit 21 from a 10-K filing."""

    def __init__(self, processed_dir: Path | str | None = None):
        settings = get_settings()
        self.processed_dir = Path(processed_dir or settings.sec.processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def parse_filing(self, metadata: FilingMetadata, ten_k: Any) -> ParsedFiling:
        """Parse structured sections and Exhibit 21 from filing object."""
        accession = metadata.accession
        filing_dir = self.processed_dir / accession
        filing_dir.mkdir(parents=True, exist_ok=True)

        sections: list[SectionContent] = []

        # 1. Item 1: Business
        item1_text = ""
        if hasattr(ten_k, "business") and ten_k.business:
            item1_text = str(ten_k.business)
        elif hasattr(ten_k, "items") and "Item 1" in ten_k.items:
            item1_text = str(ten_k["Item 1"])
        item1_clean = clean_section_text(item1_text)
        if item1_clean:
            h1 = hashlib.sha256(item1_clean.encode("utf-8")).hexdigest()
            sections.append(
                SectionContent(
                    item="item1",
                    section_name="Item 1. Business",
                    text=item1_clean,
                    char_count=len(item1_clean),
                    sha256=h1,
                )
            )

        # 2. Item 1A: Risk Factors
        item1a_text = ""
        if hasattr(ten_k, "risk_factors") and ten_k.risk_factors:
            item1a_text = str(ten_k.risk_factors)
        elif hasattr(ten_k, "items") and "Item 1A" in ten_k.items:
            item1a_text = str(ten_k["Item 1A"])
        item1a_clean = clean_section_text(item1a_text)
        if item1a_clean:
            h1a = hashlib.sha256(item1a_clean.encode("utf-8")).hexdigest()
            sections.append(
                SectionContent(
                    item="item1a",
                    section_name="Item 1A. Risk Factors",
                    text=item1a_clean,
                    char_count=len(item1a_clean),
                    sha256=h1a,
                )
            )

        # 3. Item 7: MD&A
        item7_text = ""
        if hasattr(ten_k, "management_discussion") and ten_k.management_discussion:
            item7_text = str(ten_k.management_discussion)
        elif hasattr(ten_k, "items") and "Item 7" in ten_k.items:
            item7_text = str(ten_k["Item 7"])
        item7_clean = clean_section_text(item7_text)
        if item7_clean:
            h7 = hashlib.sha256(item7_clean.encode("utf-8")).hexdigest()
            sections.append(
                SectionContent(
                    item="item7",
                    section_name="Item 7. Management's Discussion and Analysis",
                    text=item7_clean,
                    char_count=len(item7_clean),
                    sha256=h7,
                )
            )

        # 4. Exhibit 21: Subsidiaries
        subsidiary_list: list[dict[str, str]] = []
        if hasattr(ten_k, "subsidiaries") and ten_k.subsidiaries:
            try:
                sub_obj = ten_k.subsidiaries
                df: pd.DataFrame = (
                    sub_obj.to_dataframe() if hasattr(sub_obj, "to_dataframe") else None
                )
                if df is not None and not df.empty:
                    # Clean columns
                    col_map = {c: c.lower().strip() for c in df.columns}
                    df = df.rename(columns=col_map)
                    name_col = next(
                        (c for c in df.columns if "name" in c or "subsidiary" in c), df.columns[0]
                    )
                    jur_col = next(
                        (
                            c
                            for c in df.columns
                            if "jurisdiction" in c or "state" in c or "country" in c
                        ),
                        None,
                    )

                    for _, row in df.iterrows():
                        sub_name = str(row[name_col]).strip()
                        jur = (
                            str(row[jur_col]).strip()
                            if jur_col and pd.notna(row[jur_col])
                            else "Unknown"
                        )
                        if sub_name and sub_name.lower() != "nan":
                            subsidiary_list.append({"name": sub_name, "jurisdiction": jur})
            except Exception as e:
                logger.warning(
                    "Error parsing subsidiaries DataFrame for %s: %s", metadata.ticker, e
                )

        # Include Exhibit 21 as a structured section for provenance and chunking
        if subsidiary_list:
            ex21_text = f"Exhibit 21 - Subsidiaries of {metadata.company}:\n" + "\n".join(
                f"- {s['name']} (Jurisdiction: {s['jurisdiction']})" for s in subsidiary_list
            )
            h_ex21 = hashlib.sha256(ex21_text.encode("utf-8")).hexdigest()
            sections.append(
                SectionContent(
                    item="exhibit21",
                    section_name="Exhibit 21. Subsidiaries",
                    text=ex21_text,
                    char_count=len(ex21_text),
                    sha256=h_ex21,
                )
            )

        # Save to disk for provenance
        summary_file = filing_dir / "parsed_summary.json"
        parsed = ParsedFiling(
            metadata=metadata,
            sections=sections,
            subsidiaries_count=len(subsidiary_list),
            subsidiaries=subsidiary_list,
        )
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(parsed.model_dump(), f, indent=2)

        return parsed
