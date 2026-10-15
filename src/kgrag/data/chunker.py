"""Section-aware text chunker with stable chunk IDs (PRD FR-1.2)."""

import logging
from typing import Any

from pydantic import BaseModel

from kgrag.config import get_settings
from kgrag.data.sec_parser import SectionContent

logger = logging.getLogger(__name__)


class ChunkRecord(BaseModel):
    chunk_id: str
    doc_id: str
    section_path: str
    item: str
    text: str
    token_count: int
    char_start: int
    char_end: int
    chunker_version: str = "v1.0"


def estimate_tokens(text: str) -> int:
    """Estimate token count based on whitespace and punctuation tokens."""
    return max(1, int(len(text.split()) * 1.3))


class SectionChunker:
    """Section-aware chunker targeting 600-800 tokens with 100-token overlap."""

    def __init__(
        self,
        target_tokens: int | None = None,
        overlap_tokens: int | None = None,
        min_tokens: int | None = None,
        max_tokens: int | None = None,
    ):
        settings = get_settings().chunking
        self.target_tokens = target_tokens or settings.target_tokens
        self.overlap_tokens = overlap_tokens or settings.overlap_tokens
        self.min_tokens = min_tokens or settings.min_tokens
        self.max_tokens = max_tokens or settings.max_tokens

    def chunk_section(self, accession: str, section: SectionContent) -> list[ChunkRecord]:
        """Split a section text into contiguous chunks without splitting mid-table rows."""
        full_text = section.text
        if not full_text.strip():
            return []

        # Split into semantic blocks (paragraphs or table blocks)
        raw_paragraphs = full_text.split("\n\n")
        blocks: list[dict[str, Any]] = []

        current_offset = 0
        for para in raw_paragraphs:
            para_len = len(para)
            start = full_text.find(para, current_offset)
            if start == -1:
                start = current_offset
            end = start + para_len
            current_offset = end

            blocks.append(
                {
                    "text": para,
                    "start": start,
                    "end": end,
                    "tokens": estimate_tokens(para),
                }
            )

        chunks: list[ChunkRecord] = []
        chunk_idx = 0
        i = 0
        total_blocks = len(blocks)

        while i < total_blocks:
            current_chunk_blocks: list[dict[str, Any]] = []
            accumulated_tokens = 0

            j = i
            while j < total_blocks:
                b = blocks[j]
                if (
                    accumulated_tokens + b["tokens"] > self.max_tokens
                    and accumulated_tokens >= self.min_tokens
                ):
                    break
                current_chunk_blocks.append(b)
                accumulated_tokens += b["tokens"]
                j += 1

            if not current_chunk_blocks:
                # Single paragraph exceeds max_tokens; take it as its own chunk
                current_chunk_blocks.append(blocks[i])
                j = i + 1

            chunk_text = "\n\n".join(b["text"] for b in current_chunk_blocks)
            char_start = current_chunk_blocks[0]["start"]
            char_end = current_chunk_blocks[-1]["end"]
            token_count = estimate_tokens(chunk_text)

            chunk_id = f"{accession}:{section.item}:{chunk_idx:04d}"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    doc_id=accession,
                    section_path=section.section_name,
                    item=section.item,
                    text=chunk_text,
                    token_count=token_count,
                    char_start=char_start,
                    char_end=char_end,
                )
            )
            chunk_idx += 1

            if j >= total_blocks:
                break

            # Calculate overlap: step back blocks until accumulated tokens >= overlap_tokens
            overlap_accum = 0
            step_back = 0
            for k in range(j - 1, i, -1):
                overlap_accum += blocks[k]["tokens"]
                step_back += 1
                if overlap_accum >= self.overlap_tokens:
                    break

            # Advance i ensuring progress
            next_i = max(i + 1, j - step_back)
            i = next_i

        return chunks
