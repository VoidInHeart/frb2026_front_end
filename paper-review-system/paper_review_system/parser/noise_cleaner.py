from __future__ import annotations

import re
from collections import Counter

from paper_review_system.models import PaperBlock, PaperDocument


class NoiseCleaner:
    """Mark headers, footers and boilerplate as noise while keeping raw blocks."""

    def clean(self, document: PaperDocument) -> list[PaperBlock]:
        repeated_candidates = self._find_repeated_edge_text(document.blocks)
        cleaned: list[PaperBlock] = []

        for block in document.blocks:
            normalized = self._normalize(block.text)
            is_noise = (
                block.is_noise
                or normalized in repeated_candidates
                or self._looks_like_page_number(block.text)
                or self._looks_like_running_header(block)
            )
            cleaned.append(
                PaperBlock(
                    block_id=block.block_id,
                    page=block.page,
                    bbox=block.bbox,
                    type=block.type,
                    text=block.text,
                    level=block.level,
                    is_noise=is_noise,
                    font_size=block.font_size,
                    source=block.source,
                    role=block.role,
                )
            )
        return cleaned

    def _find_repeated_edge_text(self, blocks: list[PaperBlock]) -> set[str]:
        counts: Counter[str] = Counter()
        for block in blocks:
            if self._is_near_page_edge(block):
                normalized = self._normalize(block.text)
                if normalized:
                    counts[normalized] += 1
        return {text for text, count in counts.items() if count >= 2}

    @staticmethod
    def _is_near_page_edge(block: PaperBlock) -> bool:
        top = block.bbox[1]
        bottom = block.bbox[3]
        return top <= 70 or bottom >= 760

    @staticmethod
    def _looks_like_page_number(text: str) -> bool:
        stripped = text.strip()
        return bool(re.fullmatch(r"(page\s*)?\d{1,4}", stripped, re.IGNORECASE))

    @staticmethod
    def _looks_like_running_header(block: PaperBlock) -> bool:
        text = re.sub(r"\s+", " ", block.text).strip().lower()
        if block.role == "header_footer" or block.type == "metadata":
            return True
        if block.role == "caption":
            return False
        return (
            ("arxiv:" in text)
            or ("copyright" in text)
            or ("preprint" in text)
            or ("accepted at" in text)
        )

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().lower()
