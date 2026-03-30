from __future__ import annotations

import re

from paper_review_system.models import PaperBlock


class MarkdownRenderer:
    """Render parser output into the anchor-list markdown format."""

    def clean_text(self, text: str) -> str:
        normalized = []
        for line in text.splitlines():
            line = line.strip()
            line = re.sub(r"[ \t\u3000]+", " ", line)
            if line:
                normalized.append(line)
        return "\n".join(normalized)

    def render_page_marker(self, page_no: int) -> list[str]:
        return [f"[Page {page_no}]", ""]

    def render_text_anchor(self, anchor_id: str) -> list[str]:
        return [f"[Anchor: {anchor_id}]"]

    def render_text_block(self, block: PaperBlock) -> list[str]:
        text = self.clean_text(block.text)
        if not text:
            return []

        if block.type == "heading":
            level = min(block.level or 2, 6)
            return [f"{'#' * level} {text}", ""]

        if block.type == "caption":
            return [f"> {text}", ""]

        if block.type == "formula":
            return ["```math", *text.splitlines(), "```", ""]

        return [*text.splitlines(), ""]

    def render_figure_ref(self, figure_ref: dict[str, str | int]) -> list[str]:
        return [
            f"[FigureRef: {figure_ref['figure_id']}]",
            f"- anchor_id: {figure_ref['anchor_id']}",
            f"- page_no: {figure_ref['page_no']}",
            f"- caption: {figure_ref['caption']}",
            f"- image_path: {figure_ref['image_path']}",
            "",
            f"![{figure_ref['figure_id']}]({figure_ref['image_path']})",
            "",
        ]

    def render_table_ref(self, table_ref: dict[str, str | int], block: PaperBlock) -> list[str]:
        lines = [
            f"[TableRef: {table_ref['table_id']}]",
            f"- anchor_id: {table_ref['anchor_id']}",
            f"- page_no: {table_ref['page_no']}",
            f"- caption: {table_ref['caption']}",
            f"- table_path: {table_ref['table_path']}",
            f"- screenshot_path: {table_ref['screenshot_path']}",
            "",
        ]
        lines.extend(self.render_table_markdown(block))
        lines.append("")
        return lines

    def render_table_markdown(self, block: PaperBlock) -> list[str]:
        headers = list(block.table_headers or [])
        rows = [list(row) for row in (block.table_rows or [])]

        if not rows:
            text = self.clean_text(block.text)
            return ["```text", *text.splitlines(), "```"]

        col_count = max(len(headers), *(len(row) for row in rows))
        if not headers:
            headers = [f"Column {index}" for index in range(1, col_count + 1)]

        headers = self._pad_row(headers, col_count)
        normalized_rows = [self._pad_row(row, col_count) for row in rows]

        lines = [
            "| " + " | ".join(self._escape_cell(cell) for cell in headers) + " |",
            "| " + " | ".join("---" for _ in range(col_count)) + " |",
        ]

        for row in normalized_rows:
            lines.append("| " + " | ".join(self._escape_cell(cell) for cell in row) + " |")

        return lines

    @staticmethod
    def _pad_row(row: list[str], size: int) -> list[str]:
        padded = row[:size]
        if len(padded) < size:
            padded.extend([""] * (size - len(padded)))
        return padded

    @staticmethod
    def _escape_cell(text: str) -> str:
        return text.replace("|", "\\|").replace("\n", "<br>")
