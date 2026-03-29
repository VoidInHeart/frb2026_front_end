from __future__ import annotations

import re

from paper_review_system.models import PaperBlock


class MarkdownRenderer:
    """Render cleaned blocks into a readable markdown document."""

    def _clean_text(self, text: str) -> str:
        # Normalize kinds of spaces and keep block-internal line boundaries
        normalized = []
        for line in text.splitlines():
            # Trim and collapse multiple spaces/tabs to single
            line = line.strip()
            line = re.sub(r"[ \t\u3000]+", " ", line)

            # Chinese-specific OCR split cleanup
            while True:
                new_line = re.sub(r"([\u4E00-\u9FFF])[ \u3000]+([\u4E00-\u9FFF])", r"\1\2", line)
                new_line = re.sub(r"([\u4E00-\u9FFF])[ \u3000]+([A-Za-z0-9])", r"\1\2", new_line)
                new_line = re.sub(r"([A-Za-z0-9])[ \u3000]+([\u4E00-\u9FFF])", r"\1\2", new_line)
                new_line = re.sub(r"([\u4E00-\u9FFF])[ \u3000]+([，。！？；：、])", r"\1\2", new_line)
                new_line = re.sub(r"([，。！？；：、])[ \u3000]+([\u4E00-\u9FFF])", r"\1\2", new_line)
                if new_line == line:
                    break
                line = new_line

            if line:
                normalized.append(line)

        return "\n".join(normalized)

    def render(self, clean_blocks: list[PaperBlock]) -> str:
        lines: list[str] = []
        current_page = None
        for block in clean_blocks:
            if block.is_noise:
                continue
            text = self._clean_text(block.text)
            if not text:
                continue

            if block.page != current_page:
                if current_page is not None:
                    lines.append("")
                lines.append(f"【page {block.page}】")
                lines.append("")
                current_page = block.page

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
                lines.extend(self._render_table(block))
                lines.append("")
                continue

            if block.type == "formula":
                lines.append("```math")
                lines.extend(text.splitlines())
                lines.append("```")
                lines.append("")
                continue

            # Paragraph and other text-typed blocks: keep block line breaks
            for paragraph_line in text.splitlines():
                lines.append("　" + paragraph_line)
            lines.append("")

        markdown = "\n".join(lines).strip() + "\n"
        return markdown

    def embed_image_urls(self, content: str, images_info: list[dict]) -> str:
        """将图片URL嵌入到markdown内容中，按页面位置插入"""
        if not images_info:
            return content

        images_by_page: dict[int, list[dict]] = {}
        for img in images_info:
            page = int(img.get("page", 1))
            images_by_page.setdefault(page, []).append(img)

        lines = content.split("\n")
        result_lines = []
        current_page = None

        page_marker_re = re.compile(r"(?:【page|#\s*page)\s*(\d+)", re.IGNORECASE)

        for index, line in enumerate(lines):
            result_lines.append(line)

            marker_match = page_marker_re.search(line)
            if marker_match:
                current_page = int(marker_match.group(1))

            next_is_page_break = False
            if index + 1 < len(lines):
                next_line = lines[index + 1]
                if page_marker_re.search(next_line):
                    next_is_page_break = True

            is_last_line = index == len(lines) - 1

            if current_page is not None and (next_is_page_break or is_last_line) and current_page in images_by_page:
                result_lines.append("")
                for img in images_by_page[current_page]:
                    alt_text = f"Image {img.get('index', '?')} from page {current_page}"
                    url = img.get("url") or img.get("path") or ""
                    result_lines.append(f"![{alt_text}]({url})")
                    result_lines.append("")
                del images_by_page[current_page]

        # 处理任何页面后仍未插入的图片
        for page, imgs in sorted(images_by_page.items()):
            result_lines.append("")
            for img in imgs:
                alt_text = f"Image {img.get('index', '?')} from page {page}"
                url = img.get("url") or img.get("path") or ""
                result_lines.append(f"![{alt_text}]({url})")
                result_lines.append("")

        return "\n".join(result_lines)

    def _render_table(self, block: PaperBlock) -> list[str]:
        headers = list(block.table_headers or [])
        rows = [list(row) for row in (block.table_rows or [])]
        lines: list[str] = []
        if block.table_caption:
            caption_lines = [f"> {block.table_caption}", ""]
        else:
            caption_lines = []
        if not rows:
            if block.table_caption_position != "below":
                lines.extend(caption_lines)
            lines.extend(["```text", *block.text.splitlines(), "```"])
            if block.table_caption_position == "below" and block.table_caption:
                lines.extend(["", f"> {block.table_caption}"])
            return lines

        col_count = max(len(headers), *(len(row) for row in rows))
        if not headers:
            headers = [f"Column {index}" for index in range(1, col_count + 1)]
        headers = self._pad_row(headers, col_count)
        normalized_rows = [self._pad_row(row, col_count) for row in rows]

        if block.table_caption_position != "below":
            lines.extend(caption_lines)
        lines.extend([
            "| " + " | ".join(self._escape_cell(cell) for cell in headers) + " |",
            "| " + " | ".join("---" for _ in range(col_count)) + " |",
        ])
        for row in normalized_rows:
            lines.append("| " + " | ".join(self._escape_cell(cell) for cell in row) + " |")
        if block.table_caption_position == "below" and block.table_caption:
            lines.extend(["", f"> {block.table_caption}"])
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
