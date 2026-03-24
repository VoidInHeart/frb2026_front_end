from __future__ import annotations

import re

from paper_review_system.models import PaperBlock, Violation
from paper_review_system.rules.violation_id import ViolationIdAllocator


class CitationRuleChecker:
    def check(self, clean_blocks: list[PaperBlock], allocator: ViolationIdAllocator) -> list[Violation]:
        reference_texts: list[str] = []
        in_references = False
        citations: list[tuple[int, PaperBlock, str]] = []

        for block in clean_blocks:
            if block.is_noise:
                continue
            lower_text = block.text.lower()
            if block.type == "heading" and ("参考文献" in block.text or "references" in lower_text):
                in_references = True
                continue
            if in_references:
                reference_texts.append(block.text)
                continue
            for token in re.findall(r"\[(\d+)\]", block.text):
                citations.append((int(token), block, token))

        reference_ids = {int(token) for text in reference_texts for token in re.findall(r"\[(\d+)\]", text)}
        violations: list[Violation] = []
        for cite_id, block, raw_token in citations:
            if reference_ids and cite_id not in reference_ids:
                violations.append(
                    Violation(
                        id=allocator.next("CIT"),
                        category="Citation_Consistency",
                        title="文内引用未在参考文献中找到",
                        location=f"P{block.page}",
                        description=f"检测到引用 [{raw_token}]，但参考文献列表中未识别到对应编号。",
                        fix_type="auto_suggest",
                        original_text=block.text[:160],
                    )
                )
        return violations
