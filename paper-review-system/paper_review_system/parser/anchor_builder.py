from __future__ import annotations

from collections import defaultdict

from paper_review_system.models import PaperAnchor, PaperBlock, SectionNode


class AnchorBuilder:
    """Create stable paragraph-level anchors for evidence linking."""

    def build(self, clean_blocks: list[PaperBlock], section_tree: list[SectionNode]) -> list[PaperAnchor]:
        section_by_block_id = self._map_block_to_section(section_tree)
        counters: defaultdict[str, int] = defaultdict(int)
        anchors: list[PaperAnchor] = []

        for block in clean_blocks:
            if block.is_noise:
                continue
            section_id = section_by_block_id.get(block.block_id)
            prefix = self._anchor_prefix(section_id, block)
            counters[prefix] += 1
            anchor_id = f"{prefix}_Para_{counters[prefix]}" if block.type == "paragraph" else f"{prefix}_Blk_{counters[prefix]}"
            anchors.append(
                PaperAnchor(
                    anchor_id=anchor_id,
                    block_id=block.block_id,
                    page=block.page,
                    bbox=block.bbox,
                    text=block.text,
                    section_id=section_id,
                )
            )
        return anchors

    @staticmethod
    def _map_block_to_section(section_tree: list[SectionNode]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for node in section_tree:
            for block_id in node.block_ids:
                mapping[block_id] = node.section_id
        return mapping

    @staticmethod
    def _anchor_prefix(section_id: str | None, block: PaperBlock) -> str:
        if section_id:
            return section_id
        if block.page == 1:
            return "FrontMatter"
        return f"P{block.page}"
