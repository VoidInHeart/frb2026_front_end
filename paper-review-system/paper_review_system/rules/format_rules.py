from __future__ import annotations

import re

from paper_review_system.models import PaperBlock, Violation
from paper_review_system.rules.violation_id import ViolationIdAllocator


class FormatRuleChecker:
    def check(self, clean_blocks: list[PaperBlock], allocator: ViolationIdAllocator) -> list[Violation]:
        violations: list[Violation] = []
        heading_numbers: list[tuple[int, PaperBlock]] = []
        for block in clean_blocks:
            if block.is_noise or block.type != "heading":
                continue
            match = re.match(r"^(\d+)", block.text.strip())
            if match:
                heading_numbers.append((int(match.group(1)), block))

        for previous, current in zip(heading_numbers, heading_numbers[1:]):
            if current[0] - previous[0] > 1:
                violations.append(
                    Violation(
                        id=allocator.next("FMT"),
                        category="Structural_Format",
                        title="章节编号跳跃",
                        location=f"P{current[1].page}",
                        description=f"检测到章节编号从 {previous[0]} 跳到 {current[0]}，中间章节可能缺失或编号不连续。",
                        fix_type="manual",
                    )
                )

        if not any(block.type == "heading" and ("参考文献" in block.text or "references" in block.text.lower()) for block in clean_blocks if not block.is_noise):
            violations.append(
                Violation(
                    id=allocator.next("FMT"),
                    category="Structural_Format",
                    title="缺少参考文献章节标题",
                    location="Document",
                    description="未在解析后的标题结构中识别到“参考文献/References”章节，建议核对章节标题是否缺失或识别失败。",
                    fix_type="manual",
                )
            )
        return violations
