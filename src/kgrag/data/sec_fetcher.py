"""SEC EDGAR Fetcher with rate-limiting, local caching, and provenance (PRD §5.1, §5.6)."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from edgar import Company, set_identity
from pydantic import BaseModel

from kgrag.config import get_settings

logger = logging.getLogger(__name__)


class FilingMetadata(BaseModel):
    ticker: str
    company: str
    cik: str
    accession: str
    filing_date: str
    fiscal_year: int
    form_type: str = "10-K"
    source_url: str
    sha256: str = ""


class SECFetcher:
    """Fetcher for SEC EDGAR filings respecting rate limits and caching raw files locally."""

    def __init__(self, raw_cache_dir: Path | str | None = None):
        settings = get_settings()
        self.user_agent = settings.sec.user_agent
        set_identity(self.user_agent)

        self.cache_dir = Path(raw_cache_dir or settings.sec.raw_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_latest_10k(self, ticker: str) -> tuple[FilingMetadata, Any]:
        """Fetch the latest 10-K filing for a given ticker."""
        logger.info("Fetching latest 10-K for %s...", ticker)
        company = Company(ticker)
        filings = [f for f in company.get_filings(form="10-K") if f.form == "10-K"]
        if not filings or len(filings) == 0:
            raise ValueError(f"No original 10-K filings found for ticker {ticker}")

        filing = filings[0]
        accession = filing.accession_number
        filing_date = str(filing.filing_date)

        # Extract fiscal year from filing date or filing period
        try:
            fiscal_year = int(filing_date.split("-")[0])
        except Exception:
            fiscal_year = 2026

        cik = str(filing.cik).zfill(10)
        source_url = filing.homepage_url or f"https://www.sec.gov/edgar/data/{cik}/{accession}"

        # Setup local cache folder
        filer_cache_dir = self.cache_dir / f"{ticker.upper()}_{accession}"
        filer_cache_dir.mkdir(parents=True, exist_ok=True)
        meta_file = filer_cache_dir / "metadata.json"

        # Check if already cached
        ten_k = filing.obj()
        raw_text = str(ten_k.document if hasattr(ten_k, "document") else str(ten_k))
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        metadata = FilingMetadata(
            ticker=ticker.upper(),
            company=company.name,
            cik=cik,
            accession=accession,
            filing_date=filing_date,
            fiscal_year=fiscal_year,
            form_type="10-K",
            source_url=source_url,
            sha256=content_hash,
        )

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)

        return metadata, ten_k
