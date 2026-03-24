from __future__ import annotations

from paper_review_system.models import PaperBlock


class MarkdownRenderer:
    """Render cleaned blocks into a readable markdown document."""

    def render(self, clean_blocks: list[PaperBlock]) -> str:
        lines: list[str] = []
        for block in clean_blocks:
            if block.is_noise:
                continue
            text = block.text.strip()
            if not text:
                continue
            if block.type == "heading":
                level = min(block.level or 2, 6)
                lines.append(f"{'#' * level} {text}")
                lines.append("")
                continue
            if block.type == "caption":
                lines.append(f"> {text}")
                lines.append("")
                continue
            if block.type == "table":
                lines.append("```text")
                lines.extend(text.splitlines())
                lines.append("```")
                lines.append("")
                continue
            if block.type == "formula":
                lines.append("```math")
                lines.extend(text.splitlines())
                lines.append("```")
                lines.append("")
                continue
            lines.append(text.replace("\n", " "))
            lines.append("")
        return "\n".join(lines).strip() + "\n"
