from __future__ import annotations

import re

from paper_review_system.models import PaperBlock, SectionNode


class SectionTreeBuilder:
    """Build a lightweight section tree from cleaned blocks."""

    def build(self, clean_blocks: list[PaperBlock]) -> list[SectionNode]:
        nodes: list[SectionNode] = []
        stack: list[SectionNode] = []
        current_section: SectionNode | None = None
        untitled_counter = 0

        for block in clean_blocks:
            if block.is_noise:
                continue

            if block.type == "heading":
                level = block.level or self._infer_level_from_text(block.text)
                untitled_counter += 1
                section_id = self._make_section_id(block.text, untitled_counter)
                parent_id = None
                while stack and stack[-1].level >= level:
                    stack.pop()
                if stack:
                    parent_id = stack[-1].section_id
                node = SectionNode(
                    section_id=section_id,
                    title=block.text,
                    level=level,
                    page_start=block.page,
                    page_end=block.page,
                    block_ids=[block.block_id],
                    parent_id=parent_id,
                )
                nodes.append(node)
                stack.append(node)
                current_section = node
                continue

            if current_section is None:
                current_section = SectionNode(
                    section_id="front_matter",
                    title="Front Matter",
                    level=1,
                    page_start=block.page,
                    page_end=block.page,
                    block_ids=[],
                )
                nodes.append(current_section)
                stack = [current_section]
            current_section.block_ids.append(block.block_id)
            current_section.page_end = max(current_section.page_end, block.page)

        return nodes

    @staticmethod
    def _infer_level_from_text(text: str) -> int:
        stripped = text.strip()
        match = re.match(r"^(\d+(?:\.\d+)*)", stripped)
        if not match:
            return 2
        return min(match.group(1).count(".") + 2, 6)

    @staticmethod
    def _make_section_id(text: str, fallback_index: int) -> str:
        stripped = text.strip()
        match = re.match(r"^(\d+(?:\.\d+)*)", stripped)
        if match:
            return f"Sec_{match.group(1).replace('.', '_')}"
        if stripped.lower() == "abstract" or stripped.startswith("摘要"):
            return "Abstract"
        if stripped.lower() == "conclusion" or stripped.startswith("结论"):
            return "Conclusion"
        safe = "".join(ch if ch.isalnum() else "_" for ch in stripped).strip("_")
        return safe[:40] or f"Section_{fallback_index}"
