"""Structured LLM extraction pipeline with caching, retries, and quote verification (PRD FR-1.3)."""

import hashlib
import json
import logging
import time
from typing import Any
from psycopg.types.json import Jsonb

from kgrag.config import get_ontology, get_settings
from kgrag.db.postgres import get_connection
from kgrag.extract.prefilter import ChunkPreFilter
from kgrag.extract.schemas import ExtractionResult
from kgrag.extract.verifier import resolve_self_reference, verify_evidence_quote
from kgrag.llm.client import LLMClient, get_llm_client

logger = logging.getLogger(__name__)

# Non-benchmark few-shot examples
FEW_SHOT_EXAMPLES = """
Example 1:
Chunk: "In October 2023, Intel Corporation entered into an agreement to supply advanced semiconductor packaging services to Cisco Systems, Inc. for its next-generation networking switches."
Filer: "Intel Corporation" (INTC)
Extraction Output:
{
  "chunk_id": "example_chunk_01",
  "relations": [
    {
      "head_name": "Intel Corporation",
      "head_type": "Company",
      "relation": "SUPPLIES_TO",
      "tail_name": "Cisco Systems, Inc.",
      "tail_type": "Company",
      "evidence_quote": "Intel Corporation entered into an agreement to supply advanced semiconductor packaging services to Cisco Systems, Inc.",
      "confidence": 0.95
    }
  ]
}

Example 2:
Chunk: "We rely on Taiwan Semiconductor Manufacturing Company (TSMC) to fabricate all of our advanced GPU silicon wafers using their 4N process node."
Filer: "NVIDIA Corporation" (NVDA)
Extraction Output:
{
  "chunk_id": "example_chunk_02",
  "relations": [
    {
      "head_name": "NVIDIA Corporation",
      "head_type": "Company",
      "relation": "MANUFACTURED_BY",
      "tail_name": "Taiwan Semiconductor Manufacturing Company",
      "tail_type": "Company",
      "evidence_quote": "We rely on Taiwan Semiconductor Manufacturing Company (TSMC) to fabricate all of our advanced GPU silicon wafers",
      "confidence": 0.98
    }
  ]
}
"""


class LLMExtractor:
    """Structured extraction pipeline enforcing ontology constraints and evidence verification."""

    def __init__(self, llm_client: LLMClient | None = None, prefilter: ChunkPreFilter | None = None):
        self.llm = llm_client or get_llm_client()
        self.prefilter = prefilter or ChunkPreFilter()
        self.settings = get_settings()
        self.ontology = get_ontology()

        # Build relation constraint map
        self.rel_constraints: dict[str, dict[str, Any]] = {
            r["name"]: r for r in self.ontology.get("relationship_types", [])
        }
        self.model_name = getattr(self.llm, "model", self.settings.llm.model)

    def _get_cache_key(self, chunk_text: str) -> str:
        return hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()

    def get_cached_result(self, chunk_text_sha256: str) -> dict[str, Any] | None:
        """Check PostgreSQL extraction_cache for existing result."""
        sql = """
        SELECT status, result_json FROM extraction_cache
        WHERE chunk_sha256 = %(sha)s
          AND model = %(model)s
          AND prompt_version = %(p_ver)s
          AND ontology_version = %(o_ver)s
          AND schema_version = %(s_ver)s;
        """
        params = {
            "sha": chunk_text_sha256,
            "model": self.model_name,
            "p_ver": self.settings.versions.prompt_version,
            "o_ver": self.settings.versions.ontology_version,
            "s_ver": self.settings.versions.schema_version,
        }
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()

    def save_cache_result(
        self,
        chunk_text_sha256: str,
        status: str,
        result_json: dict[str, Any] | None,
        latency_ms: int = 0,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        """Persist extraction attempt into extraction_cache."""
        sql = """
        INSERT INTO extraction_cache (
            chunk_sha256, model, prompt_version, ontology_version,
            schema_version, status, result_json, tokens_in, tokens_out, latency_ms
        ) VALUES (
            %(sha)s, %(model)s, %(p_ver)s, %(o_ver)s,
            %(s_ver)s, %(status)s, %(result)s, %(tokens_in)s, %(tokens_out)s, %(latency_ms)s
        )
        ON CONFLICT (chunk_sha256, model, prompt_version, ontology_version, schema_version)
        DO UPDATE SET
            status = EXCLUDED.status,
            result_json = EXCLUDED.result_json,
            latency_ms = EXCLUDED.latency_ms;
        """
        params = {
            "sha": chunk_text_sha256,
            "model": self.model_name,
            "p_ver": self.settings.versions.prompt_version,
            "o_ver": self.settings.versions.ontology_version,
            "s_ver": self.settings.versions.schema_version,
            "status": status,
            "result": Jsonb(result_json) if result_json is not None else None,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
        }
        with get_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

    def extract_chunk(
        self,
        chunk_id: str,
        chunk_text: str,
        filer_company: str,
        filer_ticker: str,
        force: bool = False,
        persist: bool = True,
    ) -> list[dict[str, Any]]:
        """Extract validated relationships from a single chunk with caching and quote verification."""
        chunk_sha = self._get_cache_key(chunk_text)

        # 1. Check cache
        if not force:
            cached = self.get_cached_result(chunk_sha)
            if cached:
                if cached["status"] == "skipped_prefilter":
                    return []
                if cached["status"] == "success" and cached["result_json"]:
                    return cached["result_json"].get("verified_relations", [])

        # 2. Pre-filter check
        should_run, reason = self.prefilter.should_extract(chunk_text)
        if not should_run:
            self.save_cache_result(chunk_sha, status="skipped_prefilter", result_json=None)
            return []

        # 3. Formulate extraction prompt
        ontology_relations_desc = "\n".join(
            f"- {r['name']}: {r.get('description', '')} (Allowed sources: {r.get('source_type')}, Allowed targets: {r.get('target_type')})"
            for r in self.ontology.get("relationship_types", [])
        )

        prompt = f"""You are a precise corporate knowledge graph extraction system.
Analyze the following SEC 10-K source chunk for the filer: {filer_company} (Ticker: {filer_ticker}).

RULES:
1. Extract ONLY facts explicitly stated in the source text. Never extrapolate or assume.
2. In this document, 'the Company', 'we', 'our', and 'the registrant' refer to '{filer_company}'.
3. Every extracted relation MUST have an exact verbatim quote from the text in `evidence_quote`.
4. Constrain relations strictly to these allowed relation types:
{ontology_relations_desc}

FEW-SHOT EXAMPLES:
{FEW_SHOT_EXAMPLES}

TARGET SOURCE CHUNK:
Chunk ID: {chunk_id}
Filer: {filer_company} ({filer_ticker})
Text:
\"\"\"{chunk_text}\"\"\"
"""

        start_time = time.perf_counter()
        try:
            result: ExtractionResult = self.llm.generate_structured(
                prompt=prompt,
                schema=ExtractionResult,
                max_retries=self.settings.llm.max_retries,
            )
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        except Exception as e:
            logger.warning("Extraction failed for chunk %s: %s", chunk_id, e)
            self.save_cache_result(chunk_sha, status="failed", result_json={"error": str(e)})
            return []

        # 4. Validate and verify extracted relationships
        verified_relations: list[dict[str, Any]] = []

        for rel in result.relations:
            # Resolve self-references
            head = resolve_self_reference(rel.head_name, filer_company)
            tail = resolve_self_reference(rel.tail_name, filer_company)

            if (
                not head
                or not tail
                or head.lower() == tail.lower()
                or head.lower() in ("none", "null", "unknown", "n/a")
                or tail.lower() in ("none", "null", "unknown", "n/a")
            ):
                continue  # Discard invalid, reflexive, or placeholder relations

            # Verify evidence quote in chunk text
            quote_verified, match_score = verify_evidence_quote(
                rel.evidence_quote,
                chunk_text,
                threshold=self.settings.extraction.evidence_match_threshold,
            )
            if not quote_verified:
                logger.debug("Quote rejected (score %.2f): %s", match_score, rel.evidence_quote)
                continue

            # Check confidence floor
            if rel.confidence < self.settings.extraction.confidence_floor:
                continue

            # Verify ontology constraint
            rel_name = rel.relation.value
            constraint = self.rel_constraints.get(rel_name)
            if constraint:
                allowed_src = constraint.get("source_type")
                allowed_tgt = constraint.get("target_type")
                if isinstance(allowed_src, str) and rel.head_type.value != allowed_src:
                    continue
                if isinstance(allowed_tgt, str) and rel.tail_type.value != allowed_tgt:
                    continue

            # Create deterministic observation ID
            obs_seed = f"{chunk_id}:{head}:{rel_name}:{tail}:{rel.evidence_quote}"
            obs_id = f"obs_llm_{hashlib.sha256(obs_seed.encode('utf-8')).hexdigest()[:16]}"

            obs_data = {
                "observation_id": obs_id,
                "chunk_id": chunk_id,
                "extraction_method": "llm",
                "head_surface": head,
                "head_type": rel.head_type.value,
                "relation_type": rel_name,
                "tail_surface": tail,
                "tail_type": rel.tail_type.value,
                "evidence_quote": rel.evidence_quote,
                "evidence_verified": True,
                "model_confidence": rel.confidence,
                "role": rel.role,
                "year": rel.year,
                "validation_result": {
                    "quote_score": match_score,
                    "model": self.model_name,
                },
                "model": self.model_name,
                "prompt_version": self.settings.versions.prompt_version,
                "ontology_version": self.settings.versions.ontology_version,
                "schema_version": self.settings.versions.schema_version,
            }
            verified_relations.append(obs_data)

        # 5. Persist observations to database
        if persist and verified_relations:
            self._persist_observations(verified_relations)

        # 6. Save cache record
        if persist:
            self.save_cache_result(
                chunk_sha,
                status="success",
                result_json={"verified_relations": verified_relations, "extracted_count": len(result.relations)},
                latency_ms=elapsed_ms,
            )

        return verified_relations

    def _persist_observations(self, observations: list[dict[str, Any]]) -> None:
        """Insert verified LLM observations into extraction_observations."""
        sql = """
        INSERT INTO extraction_observations (
            observation_id, chunk_id, extraction_method, head_surface, head_type,
            relation_type, tail_surface, tail_type, evidence_quote, evidence_verified,
            model_confidence, role, year, validation_result, model, prompt_version,
            ontology_version, schema_version
        ) VALUES (
            %(observation_id)s, %(chunk_id)s, %(extraction_method)s, %(head_surface)s, %(head_type)s,
            %(relation_type)s, %(tail_surface)s, %(tail_type)s, %(evidence_quote)s, %(evidence_verified)s,
            %(model_confidence)s, %(role)s, %(year)s, %(validation_result)s, %(model)s, %(prompt_version)s,
            %(ontology_version)s, %(schema_version)s
        )
        ON CONFLICT (observation_id) DO UPDATE SET
            evidence_quote = EXCLUDED.evidence_quote,
            evidence_verified = EXCLUDED.evidence_verified,
            model_confidence = EXCLUDED.model_confidence;
        """
        with get_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                for obs in observations:
                    cur.execute(sql, {**obs, "validation_result": Jsonb(obs["validation_result"])})
