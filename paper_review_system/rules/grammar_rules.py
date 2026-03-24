from __future__ import annotations

import re

from paper_review_system.models import PaperBlock, Violation
from paper_review_system.rules.violation_id import ViolationIdAllocator


class GrammarRuleChecker:
    def check(self, clean_blocks: list[PaperBlock], allocator: ViolationIdAllocator) -> list[Violation]:
        violations: list[Violation] = []
        for block in clean_blocks:
            if not self._is_body_paragraph(block):
                continue
            if re.search(r"[。！？!?]{2,}", block.text):
                violations.append(
                    Violation(
                        id=allocator.next("GRM"),
                        category="Grammar_Style",
                        title="重复标点",
                        location=f"P{block.page}",
                        description="检测到连续重复的句末标点，建议统一语气并删除多余符号。",
                        fix_type="auto_suggest",
                        original_text=block.text[:160],
                    )
                )
            if len(block.text) > 280 and "，" not in block.text and "," not in block.text:
                violations.append(
                    Violation(
                        id=allocator.next("GRM"),
                        category="Grammar_Style",
                        title="句子过长且缺少停顿",
                        location=f"P{block.page}",
                        description="段落文本较长但缺少明显停顿，建议拆分句子以提升可读性。",
                        fix_type="auto_suggest",
                        original_text=block.text[:160],
                    )
                )
        return violations

    @staticmethod
    def _is_body_paragraph(block: PaperBlock) -> bool:
        if block.is_noise or block.type != "paragraph":
            return False
        if block.role and block.role != "body":
            return False
        text = re.sub(r"\s+", " ", block.text).strip()
        if not text:
            return False
        if re.match(r"^(figure|fig\.|table)\s*\d+", text, re.IGNORECASE):
            return False
        if re.match(r"^(图|表)\s*\d+", text):
            return False
        return True
