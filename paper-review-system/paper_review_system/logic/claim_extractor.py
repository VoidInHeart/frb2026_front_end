from __future__ import annotations

import re
from collections import Counter

from paper_review_system.models import PaperAnchor, PaperBlock

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "using",
    "我们",
    "本文",
    "研究",
    "结果",
    "方法",
    "以及",
    "进行",
    "通过",
    "一个",
}


class ClaimExtractor:
    """Extract lightweight section claims for downstream reasoning."""

    def extract(self, blocks: list[PaperBlock], anchors: list[PaperAnchor]) -> dict[str, dict[str, object]]:
        anchor_by_block_id = {anchor.block_id: anchor for anchor in anchors}
        claims: dict[str, dict[str, object]] = {}

        for block in blocks:
            if block.is_noise:
                continue
            anchor = anchor_by_block_id.get(block.block_id)
            if not anchor or not anchor.section_id:
                continue
            entry = claims.setdefault(anchor.section_id, {"anchors": [], "text": [], "keywords": []})
            entry["anchors"].append(anchor.anchor_id)
            entry["text"].append(block.text)
            entry["keywords"].extend(self._keywords(block.text))

        for section_id, payload in claims.items():
            keywords = Counter(payload["keywords"]).most_common(8)
            claims[section_id] = {
                "anchors": payload["anchors"],
                "summary": self._summarize(payload["text"]),
                "keywords": [item[0] for item in keywords],
            }
        return claims

    @staticmethod
    def _keywords(text: str) -> list[str]:
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]{2,}", text)
        return [token.lower() for token in tokens if token.lower() not in STOPWORDS]

    @staticmethod
    def _summarize(texts: list[str]) -> str:
        joined = " ".join(texts).strip()
        if len(joined) <= 220:
            return joined
        return joined[:217].rstrip() + "..."
