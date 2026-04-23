from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import hashlib
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict


class DoclingNotInstalledError(RuntimeError):
    pass


FORMULA_PLACEHOLDER = "<!-- formula-not-decoded -->"
MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
ASSET_PATH_RE = re.compile(r"\((assets\\[^)\s]+)\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((assets/[^)]+)\)")
TABLE_CAPTION_HEADING_RE = re.compile(r"^(?:\u8868|table)\s*\d+\s+.+$", re.IGNORECASE)
ALGORITHM_INLINE_HEADING_RE = re.compile(
    r"^(?:"
    r"\u7b97\u6cd5\s*[:\uff1a].+|"
    r"algorithm\s*[:\uff1a].+|"
    r"synthesis|"
    r"input(?:\s*[:\uff1a].*)?|"
    r"output(?:\s*[:\uff1a].*)?|"
    r"\u8f93\u5165(?:\s*[:\uff1a].*)?|"
    r"\u8f93\u51fa(?:\s*[:\uff1a].*)?|"
    r"\d+\.\s*return\b.*"
    r")$",
    re.IGNORECASE,
)
NUMBER_ONLY_HEADING_RE = re.compile(
    r"^(?:第[一二三四五六七八九十百千零〇两]+章|[0-9]+(?:\.[0-9]+)*\.?|\([0-9]+\))$"
)
SECTION_NUMBER_PREFIX_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)+)\s*(.*)$")
PAREN_CN_SECTION_RE = re.compile(
    r"^\uFF08[\u4E00\u4E8C\u4E09\u56DB\u4E94\u516D\u4E03\u516B\u4E5D\u5341\u767E\u5343\u96F6\u3007\u4E24]+\uFF09\s*.*$"
)
CN_ORDERED_CHAPTER_RE = re.compile(
    r"^[\u4E00\u4E8C\u4E09\u56DB\u4E94\u516D\u4E03\u516B\u4E5D\u5341\u767E\u5343\u96F6\u3007\u4E24]+[、.]\s*.+$"
)
SINGLE_ARABIC_HEADING_RE = re.compile(r"^\d+[.)]\s+.+$")
RELATED_WORK_CHAPTER_RE = re.compile(r"(相关研究|国内外研究|研究现状|文献综述|related\s+work)", re.IGNORECASE)
RELATED_WORK_CHILD_RE = re.compile(r"(国内|国外|相关研究|研究现状|动机|观察|综述)")
CHAPTER_HEADING_RE = re.compile(r"^第([一二三四五六七八九十百千零〇两]+)章(?:\s+.*)?$")
MATH_LIKE_HEADING_RE = re.compile(r"[=∈∑∏√≤≥≈]")
FORMULA_INTRO_CUE_RE = re.compile(
    r"(表示为|可表示为|定义为|定义如下|可定义为|形式如下|满足以下关系|集合为以下形式|构成的集合为|如下所示)\s*[:：]?\s*$"
)
ENUM_ONLY_BULLET_RE = re.compile(r"^-\s*\((\d+)\)\s*$")
ENUM_INLINE_BULLET_RE = re.compile(r"^-\s*\((\d+)\)\s+(.+)$")
GENERIC_BULLET_RE = re.compile(r"^-\s+(.+)$")
LEADING_FOOTER_NUMBER_RE = re.compile(r"^\d+\.\s+(?=[\u4e00-\u9fff])")
FIGURE_CAPTION_AT_END_RE = re.compile(r"\s+(图\s*\d+\s+.+)$")
FIGURE_CAPTION_LINE_RE = re.compile(r"^图\s*\d+\s+.+$")
IMAGE_LINE_RE = re.compile(r"^!\[.*?\]\(.+\)$")
FORMULA_NUMBER_ONLY_RE = re.compile(r"^\(\d+\)$")
SHORT_LABEL_PARAGRAPH_RE = re.compile(r"^[\u4e00-\u9fffA-Za-z0-9_\-/ ]{2,16}[。:：]")
EMBEDDED_LABEL_PARAGRAPH_RE = re.compile(
    r"^(?P<prefix>.*?[：:])\s*(?P<label>[\u4e00-\u9fffA-Za-z0-9_\-/ ]{2,16}[。:：].+)$"
)
FRONT_MATTER_HEADING_KEYWORDS = (
    "独创性声明",
    "使用授权书",
    "学位论文使用授权书",
    "关于学位论文的独创性声明",
    "目录",
    "目 录",
    "插图清单",
    "附表清单",
    "插表清单",
    "表格清单",
    "图表清单",
)
ABSTRACT_HEADING_KEYWORDS = ("摘要", "abstract")
INLINE_RPU_BODY_HEADINGS = (
    "Structure Feature",
    "Analyse Webpage Content",
    "Understand Domian Knowledge",
    "Identify Mentioned Code Elements",
    "Identify Feature-related Files",
    "Identify Feature-related Code Elements",
    "Identify Feature-Related Code Snippets",
    "Consult Relevant Code Context",
    "Consult Dependent Code",
    "Select Regression Test",
    "Analyse Test Scenarios",
    "Write Test Code",
    "Fix Test  Code",
    "Fix Test Code",
    "Evaluate Test Availability",
    "Decide Coding Strategy",
    "Apply Code Changes",
    "Decide Modification Strategy",
    "Fix Patch",
    "Minimise Patch",
    "Augment Patch",
    "Evaluate Patch Adequacy",
)
INLINE_RPU_BODY_SPLIT_RE = re.compile(
    r"(?<!^)(?=(?:"
    + "|".join(re.escape(item) for item in INLINE_RPU_BODY_HEADINGS)
    + r")\b)"
)
BROKEN_ANALYSE_WEBPAGE_PREFIX_RE = re.compile(r"^实现。首先提取需求中.*实现新功能相$")
BROKEN_ANALYSE_WEBPAGE_LINE_RE = re.compile(
    r"^Analyse Webpage Content\s*。该过程基于网络请求接口与 LLM 的网页链接；然后基于网络请求接口提取相关内容；最后由 LLM 关的内容。$"
)
CANONICAL_ANALYSE_WEBPAGE_LINE = (
    "Analyse Webpage Content 。该过程基于网络请求接口与 LLM 实现。"
    "首先提取需求中的网页链接；然后基于网络请求接口提取相关内容；"
    "最后由 LLM 提取与实现新功能相关的内容。"
)


def _normalize_heading_text(title: str) -> str:
    normalized_title = _normalize_compatibility_cjk_chars(str(title or ""))
    return re.sub(r"\s+", "", normalized_title).strip().lower()


def _normalize_compatibility_cjk_chars(text: str) -> str:
    normalized_chars: list[str] = []

    for char in str(text or ""):
        codepoint = ord(char)
        if 0x2E80 <= codepoint <= 0x2FDF or 0xF900 <= codepoint <= 0xFAFF:
            normalized_chars.append(unicodedata.normalize("NFKC", char))
            continue
        normalized_chars.append(char)

    return "".join(normalized_chars)


def _normalize_asset_paths(markdown: str) -> str:
    def replace_path(match: re.Match[str]) -> str:
        raw_path = match.group(1)
        return f"({raw_path.replace('\\', '/')})"

    return ASSET_PATH_RE.sub(replace_path, markdown)


def _parse_markdown_blocks(markdown: str) -> tuple[list[str], list[dict[str, Any]]]:
    leading_lines: list[str] = []
    blocks: list[dict[str, Any]] = []
    current_block: dict[str, Any] | None = None

    def flush_current() -> None:
        nonlocal current_block
        if current_block is None:
            return
        blocks.append(current_block)
        current_block = None

    for raw_line in markdown.splitlines():
        match = MARKDOWN_HEADING_RE.match(raw_line.strip())
        if match:
            flush_current()
            current_block = {
                "level": len(match.group(1)),
                "title": match.group(2).strip(),
                "body": [],
            }
            continue

        if current_block is None:
            leading_lines.append(raw_line)
            continue
        current_block["body"].append(raw_line)

    flush_current()
    return leading_lines, blocks


def _render_markdown_blocks(leading_lines: list[str], blocks: list[dict[str, Any]]) -> str:
    out_lines: list[str] = [line for line in leading_lines if line.strip()]

    for block in blocks:
        if out_lines:
            out_lines.append("")
        out_lines.append(f"{'#' * int(block['level'])} {str(block['title']).strip()}")
        body_lines = list(block.get("body", []))
        if body_lines:
            out_lines.extend(body_lines)

    return "\n".join(out_lines).strip() + "\n"


def _is_special_body_line(text: str) -> bool:
    stripped = text.strip()
    return (
        not stripped
        or stripped.startswith(("|", "![", "```", "$$", ">"))
        or bool(FIGURE_CAPTION_LINE_RE.match(stripped))
        or stripped == FORMULA_PLACEHOLDER
    )


def _ends_like_sentence(text: str) -> bool:
    stripped = text.rstrip()
    return stripped.endswith(("。", "；", "：", "！", "？", ".", ";", ":", "!", "?", "）", ")"))


def _can_merge_paragraph_lines(previous: str, current: str) -> bool:
    prev = previous.strip()
    curr = current.strip()
    if not prev or not curr:
        return False
    if _is_special_body_line(prev) or _is_special_body_line(curr):
        return False
    if prev.startswith("- ") or curr.startswith("- "):
        return False
    return not _ends_like_sentence(prev)


def _is_plain_paragraph_line(text: str) -> bool:
    stripped = str(text or "").strip()
    return bool(stripped) and not _is_special_body_line(stripped) and not stripped.startswith("- ")


def _split_inline_rpu_body_lines(lines: list[str]) -> list[str]:
    split_lines: list[str] = []

    for raw_line in lines:
        stripped = str(raw_line or "").strip()
        if not stripped or _is_special_body_line(stripped) or stripped.startswith("- "):
            split_lines.append(raw_line)
            continue

        pieces = [
            _normalize_inline_spacing(piece.strip())
            for piece in INLINE_RPU_BODY_SPLIT_RE.split(stripped)
            if piece.strip()
        ]
        if len(pieces) <= 1:
            split_lines.append(raw_line)
            continue

        if split_lines and split_lines[-1] != "":
            split_lines.append("")
        for index, piece in enumerate(pieces):
            if index > 0 and split_lines and split_lines[-1] != "":
                split_lines.append("")
            split_lines.append(piece)

    return split_lines


def _normalize_inline_spacing(text: str) -> str:
    normalized = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    normalized = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[，。；：！？、】【》）])", "", normalized)
    normalized = re.sub(r"(?<=[（【《])\s+(?=[\u4e00-\u9fff])", "", normalized)
    return normalized.strip()


def _split_embedded_figure_caption(line: str, next_nonempty_line: str | None) -> list[str]:
    if not line:
        return []

    normalized_line = LEADING_FOOTER_NUMBER_RE.sub("", line.strip(), count=1)
    if not next_nonempty_line or not next_nonempty_line.strip().startswith("!["):
        return [_normalize_inline_spacing(normalized_line)]

    match = FIGURE_CAPTION_AT_END_RE.search(normalized_line)
    if not match:
        return [_normalize_inline_spacing(normalized_line)]

    paragraph = _normalize_inline_spacing(normalized_line[: match.start()].strip())
    caption = _normalize_inline_spacing(match.group(1).strip())
    output: list[str] = []
    if paragraph:
        output.append(paragraph)
    if caption:
        output.append(caption)
    return output


def _looks_like_label_paragraph_start(line: str) -> bool:
    stripped = str(line or "").strip()
    if not stripped:
        return False
    return bool(SHORT_LABEL_PARAGRAPH_RE.match(stripped))


def _reflow_interrupted_figure_blocks(lines: list[str]) -> list[str]:
    reordered: list[str] = []
    index = 0

    while index < len(lines):
        current = lines[index]
        if (
            current.strip()
            and not _is_special_body_line(current)
            and not _ends_like_sentence(current)
            and index + 1 < len(lines)
            and FIGURE_CAPTION_LINE_RE.match(lines[index + 1].strip())
        ):
            image_index = index + 2
            if image_index < len(lines) and not lines[image_index].strip():
                image_index += 1
            continuation_index = image_index + 1
            if image_index < len(lines) and lines[image_index].strip().startswith("!["):
                if continuation_index < len(lines) and not lines[continuation_index].strip():
                    continuation_index += 1
                if continuation_index < len(lines):
                    continuation = lines[continuation_index]
                    if continuation.strip() and not _is_special_body_line(continuation):
                        if _looks_like_label_paragraph_start(continuation):
                            reordered.append(current)
                            index += 1
                            continue
                        reordered.append(
                            _normalize_inline_spacing(f"{current.rstrip()} {continuation.lstrip()}")
                        )
                        reordered.append("")
                        reordered.append(lines[index + 1].strip())
                        reordered.append("")
                        reordered.append(lines[image_index].strip())
                        index = continuation_index + 1
                        continue

        reordered.append(current)
        index += 1

    return reordered


def _merge_formula_number_blocks(lines: list[str]) -> list[str]:
    merged: list[str] = []
    index = 0

    while index < len(lines):
        if (
            index + 6 < len(lines)
            and lines[index].strip() == "$$"
            and lines[index + 2].strip() == "$$"
            and lines[index + 3].strip() == ""
            and lines[index + 4].strip() == "$$"
            and FORMULA_NUMBER_ONLY_RE.fullmatch(lines[index + 5].strip())
            and lines[index + 6].strip() == "$$"
        ):
            formula_line = lines[index + 1].rstrip()
            formula_number = lines[index + 5].strip()
            merged.extend(["$$", f"{formula_line} {formula_number}".strip(), "$$"])
            index += 7
            continue

        merged.append(lines[index])
        index += 1

    return merged


def _move_embedded_label_paragraphs_after_figures(lines: list[str]) -> list[str]:
    reordered: list[str] = []
    index = 0

    while index < len(lines):
        current = lines[index]
        match = EMBEDDED_LABEL_PARAGRAPH_RE.match(current.strip())
        if match and index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            if FIGURE_CAPTION_LINE_RE.match(next_line):
                image_index = index + 2
                if image_index < len(lines) and not lines[image_index].strip():
                    image_index += 1
                if image_index < len(lines) and lines[image_index].strip().startswith("!["):
                    prefix = _normalize_inline_spacing(match.group("prefix").strip())
                    label_paragraph = _normalize_inline_spacing(match.group("label").strip())
                    if prefix:
                        reordered.append(prefix)
                    reordered.append("")
                    reordered.append(lines[index + 1].strip())
                    reordered.append("")
                    reordered.append(lines[image_index].strip())
                    reordered.append("")
                    reordered.append(label_paragraph)
                    index = image_index + 1
                    continue

        reordered.append(current)
        index += 1

    return reordered


def _is_table_line(text: str) -> bool:
    return str(text or "").strip().startswith("|")


def _is_image_line(text: str) -> bool:
    return bool(IMAGE_LINE_RE.match(str(text or "").strip()))


def _normalize_media_block_spacing(lines: list[str]) -> list[str]:
    normalized: list[str] = []

    for index, raw_line in enumerate(lines):
        stripped = str(raw_line or "").strip()
        if not stripped:
            if normalized and normalized[-1] != "":
                normalized.append("")
            continue

        previous_nonempty = ""
        for candidate in reversed(normalized):
            if candidate.strip():
                previous_nonempty = candidate.strip()
                break

        if _is_image_line(stripped) and previous_nonempty and normalized and normalized[-1] != "":
            normalized.append("")

        normalized.append(stripped)

        next_nonempty = ""
        for probe in lines[index + 1 :]:
            candidate = str(probe or "").strip()
            if candidate:
                next_nonempty = candidate
                break

        if _is_image_line(stripped) and next_nonempty and not _is_image_line(next_nonempty):
            normalized.append("")

    while normalized and not normalized[-1].strip():
        normalized.pop()
    return normalized


def _normalize_table_block_spacing(lines: list[str]) -> list[str]:
    normalized: list[str] = []

    for index, raw_line in enumerate(lines):
        stripped = str(raw_line or "").strip()
        if not stripped:
            if normalized and normalized[-1] != "":
                normalized.append("")
            continue

        is_table_line = _is_table_line(stripped)
        previous_nonempty = ""
        for candidate in reversed(normalized):
            if candidate.strip():
                previous_nonempty = candidate.strip()
                break

        if is_table_line and previous_nonempty and not _is_table_line(previous_nonempty):
            if normalized[-1] != "":
                normalized.append("")

        normalized.append(stripped)

        next_nonempty = ""
        for probe in lines[index + 1 :]:
            candidate = str(probe or "").strip()
            if candidate:
                next_nonempty = candidate
                break

        if is_table_line and next_nonempty and not _is_table_line(next_nonempty):
            normalized.append("")

    while normalized and not normalized[-1].strip():
        normalized.pop()
    return normalized


def _repair_feature_analysis_rpu_lines(lines: list[str]) -> list[str]:
    repaired: list[str] = []

    for raw_line in lines:
        stripped = _normalize_inline_spacing(str(raw_line or "").strip())
        if not stripped:
            repaired.append(raw_line)
            continue

        if BROKEN_ANALYSE_WEBPAGE_PREFIX_RE.match(stripped):
            continue

        if BROKEN_ANALYSE_WEBPAGE_LINE_RE.match(stripped):
            repaired.append(CANONICAL_ANALYSE_WEBPAGE_LINE)
            continue

        if stripped.startswith("Structure  Feature"):
            repaired.append(stripped.replace("Structure  Feature", "Structure Feature", 1))
            continue

        repaired.append(raw_line)

    return repaired


def _normalize_block_body(body_lines: list[str]) -> list[str]:
    normalized: list[str] = []
    pending_enum: str | None = None
    pending_blank = False

    for index, raw_line in enumerate(body_lines):
        stripped = raw_line.strip()

        if not stripped:
            pending_blank = True
            continue

        next_nonempty_line = None
        for next_index in range(index + 1, len(body_lines)):
            candidate = body_lines[next_index].strip()
            if candidate:
                next_nonempty_line = candidate
                break

        expanded_lines = _split_embedded_figure_caption(stripped, next_nonempty_line)
        for expanded_line in expanded_lines:
            enum_only_match = ENUM_ONLY_BULLET_RE.match(expanded_line)
            if enum_only_match:
                pending_enum = enum_only_match.group(1)
                pending_blank = False
                continue

            current_line = _normalize_inline_spacing(expanded_line)
            generic_bullet_match = GENERIC_BULLET_RE.match(current_line)

            if pending_enum is not None:
                if generic_bullet_match:
                    current_line = f"- ({pending_enum}) {generic_bullet_match.group(1).strip()}"
                else:
                    current_line = f"- ({pending_enum}) {current_line}"
                pending_enum = None
                generic_bullet_match = GENERIC_BULLET_RE.match(current_line)

            if (
                generic_bullet_match
                and normalized
                and normalized[-1].strip().startswith("- ")
                and not ENUM_ONLY_BULLET_RE.match(normalized[-1].strip())
                and not ENUM_INLINE_BULLET_RE.match(generic_bullet_match.group(0))
                and not _ends_like_sentence(normalized[-1])
            ):
                normalized[-1] = f"{normalized[-1].rstrip()} {generic_bullet_match.group(1).strip()}"
                pending_blank = False
                continue

            if not pending_blank and normalized and _can_merge_paragraph_lines(normalized[-1], current_line):
                normalized[-1] = f"{normalized[-1].rstrip()} {current_line}"
                pending_blank = False
                continue

            if pending_blank and normalized and normalized[-1] != "":
                normalized.append("")
            elif (
                normalized
                and normalized[-1] != ""
                and _is_plain_paragraph_line(normalized[-1])
                and _is_plain_paragraph_line(current_line)
            ):
                normalized.append("")
            normalized.append(current_line)
            pending_blank = False

    if pending_enum is not None:
        normalized.append(f"- ({pending_enum})")

    normalized = _reflow_interrupted_figure_blocks(normalized)
    normalized = _move_embedded_label_paragraphs_after_figures(normalized)
    normalized = _merge_formula_number_blocks(normalized)
    normalized = _normalize_media_block_spacing(normalized)
    normalized = _normalize_table_block_spacing(normalized)
    normalized = _split_inline_rpu_body_lines(normalized)
    normalized = _repair_feature_analysis_rpu_lines(normalized)

    while normalized and not normalized[-1].strip():
        normalized.pop()
    return normalized


def _normalize_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_blocks: list[dict[str, Any]] = []
    seen_chinese_chapter = False
    for block in blocks:
        current = dict(block)
        title = str(current.get("title", "")).strip()
        if PAREN_CN_SECTION_RE.match(title):
            current["level"] = 3
        elif seen_chinese_chapter and SINGLE_ARABIC_HEADING_RE.match(title):
            current["level"] = max(int(current.get("level", 2)), 3)
        current["body"] = _normalize_block_body(list(current.get("body", [])))
        normalized_blocks.append(current)
        if _is_chinese_ordered_chapter_title(title):
            seen_chinese_chapter = True
    return normalized_blocks


def _is_chinese_ordered_chapter_title(title: str) -> bool:
    text = str(title or "").strip()
    return bool(CN_ORDERED_CHAPTER_RE.match(text) or CHAPTER_HEADING_RE.match(text))


def _find_first_abstract_index(blocks: list[dict[str, Any]]) -> int | None:
    for index, block in enumerate(blocks):
        title_norm = _normalize_heading_text(str(block.get("title", "")))
        if any(keyword in title_norm for keyword in ABSTRACT_HEADING_KEYWORDS):
            return index
    return None


def _drop_leading_front_matter(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    abstract_index = _find_first_abstract_index(blocks)
    if abstract_index is None or abstract_index <= 0:
        return blocks
    return blocks[abstract_index:]


def _is_excluded_heading(title: str) -> bool:
    normalized = _normalize_heading_text(title)
    return any(_normalize_heading_text(keyword) in normalized for keyword in FRONT_MATTER_HEADING_KEYWORDS)


def _filter_excluded_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [block for block in blocks if not _is_excluded_heading(str(block.get("title", "")))]


def _repair_related_work_blocks_misordered_after_abstract(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    abstract_index = _find_first_abstract_index(blocks)
    if abstract_index is None:
        return blocks

    first_chapter_index: int | None = None
    for index in range(abstract_index + 1, len(blocks)):
        if _is_chinese_ordered_chapter_title(str(blocks[index].get("title", ""))):
            first_chapter_index = index
            break

    if first_chapter_index is None or first_chapter_index <= abstract_index + 1:
        return blocks

    orphan_indices: list[int] = []
    for index in range(abstract_index + 1, first_chapter_index):
        title = str(blocks[index].get("title", "")).strip()
        if not PAREN_CN_SECTION_RE.match(title):
            return blocks
        orphan_indices.append(index)

    if not orphan_indices:
        return blocks

    if not any(RELATED_WORK_CHILD_RE.search(str(blocks[index].get("title", ""))) for index in orphan_indices):
        return blocks

    target_index: int | None = None
    for index in range(first_chapter_index, len(blocks)):
        title = str(blocks[index].get("title", "")).strip()
        if _is_chinese_ordered_chapter_title(title) and RELATED_WORK_CHAPTER_RE.search(title):
            target_index = index
            break

    if target_index is None:
        return blocks

    orphan_blocks = [dict(blocks[index]) for index in orphan_indices]
    remaining = [dict(block) for index, block in enumerate(blocks) if index not in set(orphan_indices)]
    removed_before_target = sum(1 for index in orphan_indices if index < target_index)
    adjusted_target_index = target_index - removed_before_target

    return [
        *remaining[: adjusted_target_index + 1],
        *orphan_blocks,
        *remaining[adjusted_target_index + 1 :],
    ]


def _is_number_only_heading(title: str) -> bool:
    return bool(NUMBER_ONLY_HEADING_RE.fullmatch(str(title or "").strip()))


def _looks_like_formula_heading(title: str) -> bool:
    text = str(title or "").strip()
    if len(text) < 8:
        return False
    return bool(MATH_LIKE_HEADING_RE.search(text))


def _last_nonempty_line(lines: list[str]) -> str:
    for line in reversed(lines):
        stripped = str(line).strip()
        if stripped:
            return stripped
    return ""


def _should_demote_formula_heading(current: dict[str, Any], previous: dict[str, Any] | None) -> bool:
    title = str(current.get("title", "")).strip()
    if not previous or not _looks_like_formula_heading(title):
        return False

    # Only demote obviously formula-like pseudo headings, not normal headings that merely contain symbols.
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", title)
    if len(cjk_chars) > 2:
        return False
    if "=" not in title and "∈" not in title and "(" not in title:
        return False

    previous_line = _last_nonempty_line(list(previous.get("body", [])))
    if not previous_line:
        return False
    return bool(FORMULA_INTRO_CUE_RE.search(previous_line))


def _merge_split_headings(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index = 0

    while index < len(blocks):
        current = dict(blocks[index])
        current_body = [line for line in list(current.get("body", []))]
        current["body"] = current_body

        if _should_demote_formula_heading(current, merged[-1] if merged else None):
            previous_block = dict(merged[-1])
            previous_body = list(previous_block.get("body", []))
            if previous_body and previous_body[-1].strip():
                previous_body.append("")
            previous_body.extend(["$$", str(current.get("title", "")).strip(), "$$"])
            if current_body:
                previous_body.append("")
                previous_body.extend(current_body)
            previous_block["body"] = _normalize_block_body(previous_body)
            merged[-1] = previous_block
            index += 1
            continue

        if _looks_like_formula_heading(str(current.get("title", ""))) and not current_body and merged:
            merged[-1].setdefault("body", []).append(str(current.get("title", "")))
            index += 1
            continue

        if index + 1 < len(blocks):
            nxt = dict(blocks[index + 1])
            next_title = str(nxt.get("title", "")).strip()
            same_level = int(current.get("level", 2)) == int(nxt.get("level", 2))
            current_empty = not any(str(line).strip() for line in current_body)

            if current_empty and same_level and _is_number_only_heading(str(current.get("title", ""))):
                current["title"] = f"{str(current.get('title', '')).strip()} {next_title}".strip()
                current["body"] = list(nxt.get("body", []))
                merged.append(current)
                index += 2
                continue

            prefix_match = SECTION_NUMBER_PREFIX_RE.match(str(current.get("title", "")).strip())
            next_has_prefix = bool(SECTION_NUMBER_PREFIX_RE.match(next_title))
            if (
                current_empty
                and same_level
                and prefix_match
                and prefix_match.group(2).strip()
                and not next_has_prefix
                and not PAREN_CN_SECTION_RE.match(next_title)
                and len(next_title) <= 20
            ):
                current["title"] = f"{str(current.get('title', '')).strip()} {next_title}".strip()
                current["body"] = list(nxt.get("body", []))
                merged.append(current)
                index += 2
                continue

        merged.append(current)
        index += 1

    return merged


def _cn_numeral_to_int(raw: str) -> int | None:
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000}
    text = str(raw or "").strip()
    if not text:
        return None
    if text == "十":
        return 10

    total = 0
    current = 0
    for char in text:
        if char in digits:
            current = digits[char]
            continue
        if char in units:
            unit = units[char]
            if current == 0:
                current = 1
            total += current * unit
            current = 0
            continue
        return None
    return total + current if total + current > 0 else None


def _chapter_index_from_title(title: str) -> int | None:
    text = str(title or "").strip()
    cn_match = CHAPTER_HEADING_RE.match(text)
    if cn_match:
        return _cn_numeral_to_int(cn_match.group(1))

    prefix_match = SECTION_NUMBER_PREFIX_RE.match(text)
    if prefix_match:
        try:
            return int(prefix_match.group(1).split(".", 1)[0])
        except ValueError:
            return None
    return None


def _move_chapter_headings_before_children(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reordered = list(blocks)
    index = 0

    while index < len(reordered):
        title = str(reordered[index].get("title", "")).strip()
        chapter_no = _chapter_index_from_title(title)
        is_chapter_heading = bool(CHAPTER_HEADING_RE.match(title))
        if not is_chapter_heading or chapter_no is None:
            index += 1
            continue

        target_index: int | None = None
        for probe in range(index):
            probe_title = str(reordered[probe].get("title", "")).strip()
            probe_match = SECTION_NUMBER_PREFIX_RE.match(probe_title)
            if not probe_match:
                continue
            if int(probe_match.group(1).split(".", 1)[0]) == chapter_no:
                target_index = probe
                break

        if target_index is None:
            index += 1
            continue

        block = dict(reordered.pop(index))
        reordered.insert(target_index, block)
        index = target_index + 1

    return reordered


def _move_chapter_body_to_first_child(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adjusted = [dict(block) for block in blocks]

    for index, block in enumerate(adjusted):
        title = str(block.get("title", "")).strip()
        chapter_no = _chapter_index_from_title(title)
        if chapter_no is None or not CHAPTER_HEADING_RE.match(title):
            continue

        chapter_body = list(block.get("body", []))
        if not any(str(line).strip() for line in chapter_body):
            continue

        target_index: int | None = None
        for probe in range(index + 1, len(adjusted)):
            probe_title = str(adjusted[probe].get("title", "")).strip()
            probe_match = SECTION_NUMBER_PREFIX_RE.match(probe_title)
            if probe_match and int(probe_match.group(1).split(".", 1)[0]) == chapter_no:
                target_index = probe
                break

        if target_index is None:
            continue

        target_block = dict(adjusted[target_index])
        target_body = list(target_block.get("body", []))
        if target_body and target_body[-1].strip():
            target_body.append("")
        target_body.extend(chapter_body)
        target_block["body"] = _normalize_block_body(target_body)
        adjusted[target_index] = target_block

        chapter_block = dict(block)
        chapter_block["body"] = []
        adjusted[index] = chapter_block

    return adjusted


def _move_chapter_intro_paragraphs_to_parent(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adjusted = [dict(block) for block in blocks]

    for index, block in enumerate(adjusted):
        title = str(block.get("title", "")).strip()
        chapter_no = _chapter_index_from_title(title)
        if chapter_no is None or not CHAPTER_HEADING_RE.match(title):
            continue

        first_child_index: int | None = None
        for probe in range(index + 1, len(adjusted)):
            probe_title = str(adjusted[probe].get("title", "")).strip()
            probe_match = SECTION_NUMBER_PREFIX_RE.match(probe_title)
            if not probe_match:
                continue
            if int(probe_match.group(1).split(".", 1)[0]) == chapter_no:
                first_child_index = probe
                break

        if first_child_index is None:
            continue

        child_block = dict(adjusted[first_child_index])
        child_body = list(child_block.get("body", []))
        intro_line_index: int | None = None

        for line_index, raw_line in enumerate(child_body):
            stripped = str(raw_line or "").strip()
            if "本章" in stripped or "鏈珷" in stripped:
                intro_line_index = line_index
                break

        if intro_line_index is None:
            continue

        intro_line = str(child_body[intro_line_index]).strip()
        remaining_body = [
            line
            for line_index, line in enumerate(child_body)
            if line_index != intro_line_index
        ]

        chapter_block = dict(block)
        chapter_body = list(chapter_block.get("body", []))
        if chapter_body and chapter_body[-1].strip():
            chapter_body.append("")
        chapter_body.append(intro_line)
        chapter_block["body"] = _normalize_block_body(chapter_body)
        adjusted[index] = chapter_block

        child_block["body"] = _normalize_block_body(remaining_body)
        adjusted[first_child_index] = child_block

    return adjusted


def _renumber_duplicate_sibling_sections(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adjusted: list[dict[str, Any]] = []
    last_component_by_parent: dict[tuple[int, tuple[int, ...]], int] = {}

    for block in blocks:
        current = dict(block)
        title = str(current.get("title", "")).strip()
        match = SECTION_NUMBER_PREFIX_RE.match(title)
        if not match:
            adjusted.append(current)
            continue

        numbers = tuple(int(part) for part in match.group(1).split("."))
        parent_key = (int(current.get("level", 2)), numbers[:-1])
        last_component = last_component_by_parent.get(parent_key)
        assigned_numbers = numbers

        if last_component is not None and numbers[-1] <= last_component:
            assigned_numbers = numbers[:-1] + (last_component + 1,)
            current["title"] = title.replace(
                match.group(1),
                ".".join(str(part) for part in assigned_numbers),
                1,
            )

        last_component_by_parent[parent_key] = assigned_numbers[-1]
        adjusted.append(current)

    return adjusted


def _append_demoted_block_lines(
    body_lines: list[str],
    title: str,
    block_body: list[str],
) -> list[str]:
    updated = list(body_lines)
    clean_title = str(title or "").strip()
    if clean_title:
        if updated and updated[-1].strip():
            updated.append("")
        updated.append(clean_title)

    clean_body = [str(line) for line in block_body if str(line).strip()]
    if clean_body:
        if updated and updated[-1].strip():
            updated.append("")
        updated.extend(clean_body)

    return updated


def _flush_demoted_blocks(
    target_block: dict[str, Any],
    pending_captions: list[dict[str, Any]],
    pending_algorithm_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    updated_block = dict(target_block)
    body_lines = list(updated_block.get("body", []))

    if pending_algorithm_blocks and pending_captions:
        for block in pending_captions:
            body_lines = _append_demoted_block_lines(
                body_lines,
                str(block.get("title", "")),
                [],
            )

        for block in pending_algorithm_blocks:
            body_lines = _append_demoted_block_lines(
                body_lines,
                str(block.get("title", "")),
                list(block.get("body", [])),
            )

        for block in pending_captions:
            caption_body = list(block.get("body", []))
            if caption_body:
                body_lines = _append_demoted_block_lines(body_lines, "", caption_body)
    else:
        for block in pending_captions:
            body_lines = _append_demoted_block_lines(
                body_lines,
                str(block.get("title", "")),
                list(block.get("body", [])),
            )

        for block in pending_algorithm_blocks:
            body_lines = _append_demoted_block_lines(
                body_lines,
                str(block.get("title", "")),
                list(block.get("body", [])),
            )

    updated_block["body"] = body_lines
    return updated_block


def _collapse_inline_heading_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collapsed: list[dict[str, Any]] = []
    pending_captions: list[dict[str, Any]] = []
    pending_algorithm_blocks: list[dict[str, Any]] = []

    def flush_pending() -> None:
        nonlocal pending_captions, pending_algorithm_blocks
        if not collapsed or (not pending_captions and not pending_algorithm_blocks):
            return
        collapsed[-1] = _flush_demoted_blocks(
            collapsed[-1],
            pending_captions,
            pending_algorithm_blocks,
        )
        pending_captions = []
        pending_algorithm_blocks = []

    for block in blocks:
        title = str(block.get("title", "")).strip()
        if TABLE_CAPTION_HEADING_RE.match(title):
            pending_captions.append(dict(block))
            continue
        if ALGORITHM_INLINE_HEADING_RE.match(title):
            pending_algorithm_blocks.append(dict(block))
            continue

        flush_pending()
        collapsed.append(dict(block))

    flush_pending()
    return collapsed


def _normalize_recovered_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _normalize_compact_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip()


def _find_block_index_for_heading(blocks: list[dict[str, Any]], heading: str | None) -> int | None:
    if not heading:
        return None

    heading_norm = _normalize_heading_text(heading)
    if not heading_norm:
        return None

    for index, block in enumerate(blocks):
        title_norm = _normalize_heading_text(str(block.get("title", "")))
        if (
            title_norm == heading_norm
            or title_norm.startswith(heading_norm)
            or heading_norm.startswith(title_norm)
            or heading_norm in title_norm
            or title_norm in heading_norm
        ):
            return index
    return None


def _append_recovered_texts(
    blocks: list[dict[str, Any]],
    target_index: int,
    recovered_texts: list[str],
) -> None:
    if target_index < 0 or target_index >= len(blocks):
        return

    block = dict(blocks[target_index])
    body_lines = list(block.get("body", []))
    joined_norm = _normalize_recovered_text("\n".join(body_lines))
    joined_compact = _normalize_compact_text("\n".join(body_lines))

    for text in recovered_texts:
        candidate = _normalize_recovered_text(text)
        candidate_compact = _normalize_compact_text(text)
        if not candidate or candidate in joined_norm or (candidate_compact and candidate_compact in joined_compact):
            continue
        if body_lines and body_lines[-1].strip():
            body_lines.append("")
        body_lines.append(text.strip())
        joined_norm = f"{joined_norm} {candidate}".strip()
        joined_compact = f"{joined_compact}{candidate_compact}".strip()

    block["body"] = _normalize_block_body(body_lines)
    blocks[target_index] = block


def _dedupe_repeated_body_lines(body_lines: list[str]) -> list[str]:
    deduped: list[str] = []
    seen_substantive: set[str] = set()

    for raw_line in body_lines:
        stripped = raw_line.strip()
        if not stripped:
            if deduped and deduped[-1] != "":
                deduped.append("")
            continue

        compact = _normalize_compact_text(stripped)
        is_substantive_text = (
            len(compact) >= 40
            and not _is_special_body_line(stripped)
            and not stripped.startswith("- ")
        )
        if is_substantive_text:
            if compact in seen_substantive:
                continue
            seen_substantive.add(compact)

        deduped.append(stripped)

    while deduped and not deduped[-1].strip():
        deduped.pop()
    return deduped


def _unreferenced_asset_names(markdown: str, assets_root: Path | None) -> list[str]:
    if assets_root is None or not assets_root.exists():
        return []

    referenced = {
        Path(match.group(1)).name
        for match in MARKDOWN_IMAGE_RE.finditer(markdown)
        if match.group(1)
    }
    assets = sorted(
        (path for path in assets_root.glob("*.png") if path.is_file()),
        key=lambda path: (path.stat().st_ctime, path.name),
    )
    return [path.name for path in assets if path.name not in referenced]


def _find_body_line_index(body_lines: list[str], candidate_text: str) -> int | None:
    candidate_compact = _normalize_compact_text(candidate_text)
    if not candidate_compact:
        return None

    for index, raw_line in enumerate(body_lines):
        stripped = raw_line.strip()
        if not stripped:
            continue
        line_compact = _normalize_compact_text(stripped)
        if not line_compact:
            continue
        if candidate_compact in line_compact or line_compact in candidate_compact:
            return index
    return None


def _insert_recovered_texts(
    body_lines: list[str],
    insert_index: int,
    recovered_texts: list[str],
) -> list[str]:
    normalized_texts = [str(text or "").strip() for text in recovered_texts if str(text or "").strip()]
    if not normalized_texts:
        return body_lines

    insertion_lines: list[str] = []
    for text in normalized_texts:
        if insertion_lines and insertion_lines[-1] != "":
            insertion_lines.append("")
        insertion_lines.append(text)

    bounded_index = max(0, min(insert_index, len(body_lines)))
    if insertion_lines and bounded_index > 0 and body_lines[bounded_index - 1].strip():
        insertion_lines.insert(0, "")
    if insertion_lines and bounded_index < len(body_lines) and body_lines[bounded_index].strip():
        insertion_lines.append("")

    return body_lines[:bounded_index] + insertion_lines + body_lines[bounded_index:]


def _append_recovered_items(
    blocks: list[dict[str, Any]],
    target_index: int,
    recovered_items: list[dict[str, str]],
) -> None:
    if target_index < 0 or target_index >= len(blocks):
        return

    block = dict(blocks[target_index])
    body_lines = list(block.get("body", []))
    joined_norm = _normalize_recovered_text("\n".join(body_lines))
    joined_compact = _normalize_compact_text("\n".join(body_lines))
    pending_prefix: list[str] = []
    trailing_missing: list[str] = []
    anchor_index: int | None = None

    for item in recovered_items:
        text = str(item.get("text") or "").strip()
        if not text:
            continue

        candidate = _normalize_recovered_text(text)
        candidate_compact = _normalize_compact_text(text)
        is_present = bool(
            candidate
            and (candidate in joined_norm or (candidate_compact and candidate_compact in joined_compact))
        )
        if is_present:
            if pending_prefix and anchor_index is None:
                anchor_index = _find_body_line_index(body_lines, text)
                if anchor_index is None:
                    trailing_missing.extend(pending_prefix)
                pending_prefix = []
            continue

        if anchor_index is None:
            pending_prefix.append(text)
            continue

        trailing_missing.append(text)

    prefix_to_insert = pending_prefix if anchor_index is not None else []
    if prefix_to_insert:
        body_lines = _insert_recovered_texts(body_lines, anchor_index, prefix_to_insert)
        joined_norm = _normalize_recovered_text("\n".join(body_lines))
        joined_compact = _normalize_compact_text("\n".join(body_lines))
    elif pending_prefix:
        trailing_missing = pending_prefix + trailing_missing

    for text in trailing_missing:
        candidate = _normalize_recovered_text(text)
        candidate_compact = _normalize_compact_text(text)
        if candidate and (candidate in joined_norm or (candidate_compact and candidate_compact in joined_compact)):
            continue
        if body_lines and body_lines[-1].strip():
            body_lines.append("")
        body_lines.append(text)
        joined_norm = f"{joined_norm} {candidate}".strip()
        joined_compact = f"{joined_compact}{candidate_compact}".strip()

    block["body"] = _dedupe_repeated_body_lines(_normalize_block_body(body_lines))
    blocks[target_index] = block


def _chunk_item_sort_key(item: dict[str, Any]) -> tuple[int, float, float]:
    prov_entries = item.get("prov") if isinstance(item, dict) else None
    if not isinstance(prov_entries, list) or not prov_entries:
        return (0, 0.0, 0.0)

    first_prov = prov_entries[0] if isinstance(prov_entries[0], dict) else {}
    bbox = first_prov.get("bbox") if isinstance(first_prov, dict) else {}
    if not isinstance(bbox, dict):
        bbox = {}

    page_no = int(first_prov.get("page_no") or 0)
    top = float(bbox.get("t") or 0.0)
    left = float(bbox.get("l") or 0.0)
    return (page_no, -top, left)


def _recover_chunk_boundary_sections(
    markdown: str,
    doc_dict: dict[str, Any],
    assets_root: Path | None = None,
) -> str:
    chunks = doc_dict.get("chunks", []) if isinstance(doc_dict, dict) else []
    if not isinstance(chunks, list) or not chunks:
        return markdown

    leading_lines, blocks = _parse_markdown_blocks(markdown)
    if not blocks:
        return markdown

    current_active_index: int | None = None
    available_assets = _unreferenced_asset_names(markdown, assets_root)

    for chunk in chunks:
        chunk_document = chunk.get("document", {}) if isinstance(chunk, dict) else {}
        texts = chunk_document.get("texts", []) if isinstance(chunk_document, dict) else []
        if not isinstance(texts, list):
            continue
        texts = sorted(texts, key=_chunk_item_sort_key)

        recovered_items: list[dict[str, str]] = []
        first_heading: str | None = None
        last_heading: str | None = None
        encountered_heading = False

        for item in texts:
            if not isinstance(item, dict):
                continue
            raw_text = str(item.get("text") or item.get("orig") or "").strip()
            if not raw_text:
                continue

            label = str(item.get("label") or "").strip().lower()
            if label == "section_header":
                if first_heading is None:
                    first_heading = raw_text
                last_heading = raw_text
                encountered_heading = True
                continue
            if encountered_heading:
                continue
            if label == "caption":
                recovered_items.append({"kind": "caption", "text": raw_text})
                if available_assets:
                    asset_name = available_assets.pop(0)
                    recovered_items.append({"kind": "image", "text": f"![Image](assets/{asset_name})"})
                continue
            if label == "text":
                recovered_items.append({"kind": "text", "text": raw_text})

        if recovered_items and current_active_index is not None:
            _append_recovered_items(blocks, current_active_index, recovered_items)

        if last_heading:
            block_index = _find_block_index_for_heading(blocks, last_heading)
            if block_index is not None:
                current_active_index = block_index

    return _render_markdown_blocks(leading_lines, blocks)


def _find_caption_page_number(doc_dict: dict[str, Any], caption_title: str) -> int | None:
    caption_norm = _normalize_heading_text(caption_title)
    if not caption_norm:
        return None

    chunks = doc_dict.get("chunks", []) if isinstance(doc_dict, dict) else []
    if not isinstance(chunks, list):
        return None

    for chunk in chunks:
        chunk_document = chunk.get("document", {}) if isinstance(chunk, dict) else {}
        texts = chunk_document.get("texts", []) if isinstance(chunk_document, dict) else []
        if not isinstance(texts, list):
            continue

        for item in sorted(texts, key=_chunk_item_sort_key):
            if not isinstance(item, dict):
                continue
            raw_text = str(item.get("text") or item.get("orig") or "").strip()
            if _normalize_heading_text(raw_text) != caption_norm:
                continue

            prov_entries = item.get("prov")
            if not isinstance(prov_entries, list) or not prov_entries:
                continue
            first_prov = prov_entries[0] if isinstance(prov_entries[0], dict) else {}
            page_no = int(first_prov.get("page_no") or 0)
            chunk_page_start = int(chunk.get("page_start") or 0)
            if page_no <= 0 or chunk_page_start <= 0:
                continue
            return chunk_page_start + page_no - 1

    return None


def _extract_missing_pdf_page_image(
    pdf_path: Path,
    page_number: int,
    assets_root: Path,
    caption_title: str,
) -> str | None:
    try:
        import pdfplumber
    except ImportError:
        return None

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            if page_number <= 0 or page_number > len(pdf.pages):
                return None

            page = pdf.pages[page_number - 1]
            images = list(page.images or [])
            if len(images) != 1:
                return None

            image_meta = images[0]
            cropped = page.crop(
                (
                    float(image_meta["x0"]),
                    float(image_meta["top"]),
                    float(image_meta["x1"]),
                    float(image_meta["bottom"]),
                )
            )
            rendered = cropped.to_image(resolution=150)
            digest = hashlib.sha256(f"{caption_title}|{page_number}".encode("utf-8")).hexdigest()[:16]
            filename = f"image_recovered_{page_number}_{digest}.png"
            output_path = assets_root / filename
            rendered.save(str(output_path), format="PNG")
            return filename
    except Exception:
        return None

    return None


def _inject_missing_figure_images(
    markdown: str,
    doc_dict: dict[str, Any],
    pdf_path: Path | None,
    assets_root: Path | None,
) -> str:
    if pdf_path is None or assets_root is None or not pdf_path.exists() or not assets_root.exists():
        return markdown

    leading_lines, blocks = _parse_markdown_blocks(markdown)
    updated = [dict(block) for block in blocks]
    changed = False

    for index, block in enumerate(updated):
        title = str(block.get("title", "")).strip()
        if not FIGURE_CAPTION_LINE_RE.match(title):
            continue

        body_lines = [str(line) for line in list(block.get("body", []))]
        has_current_image = any(str(line).strip().startswith("![") for line in body_lines)
        has_previous_image = False
        if index > 0:
            previous_body = [str(line).strip() for line in list(updated[index - 1].get("body", []))]
            has_previous_image = any(line.startswith("![") for line in previous_body)

        if has_current_image or has_previous_image:
            continue

        page_number = _find_caption_page_number(doc_dict, title)
        if page_number is None:
            continue

        filename = _extract_missing_pdf_page_image(pdf_path, page_number, assets_root, title)
        if not filename:
            continue

        updated[index]["body"] = _normalize_block_body([f"![Image](assets/{filename})", *body_lines])
        changed = True

    if not changed:
        return markdown

    return _render_markdown_blocks(leading_lines, updated)


def _postprocess_markdown(markdown: str) -> str:
    normalized = _normalize_asset_paths(markdown)
    normalized = _normalize_compatibility_cjk_chars(normalized)
    leading_lines, blocks = _parse_markdown_blocks(normalized)
    blocks = _drop_leading_front_matter(blocks)
    blocks = _filter_excluded_blocks(blocks)
    blocks = _repair_related_work_blocks_misordered_after_abstract(blocks)
    blocks = _merge_split_headings(blocks)
    blocks = _move_chapter_headings_before_children(blocks)
    blocks = _collapse_inline_heading_blocks(blocks)
    blocks = _move_chapter_intro_paragraphs_to_parent(blocks)
    blocks = _renumber_duplicate_sibling_sections(blocks)
    blocks = _normalize_blocks(blocks)
    return _render_markdown_blocks(leading_lines, blocks)


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _log_progress(message: str) -> None:
    print(f"[docling-progress] {message}", flush=True)


def _env_bool(name: str, default: bool) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _contains_non_ascii(path: Path) -> bool:
    try:
        str(path).encode("ascii")
    except UnicodeEncodeError:
        return True
    return False


def _find_workspace_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".venv").exists():
            return candidate
    return start


def _list_subst_mappings() -> dict[str, Path]:
    result = subprocess.run(
        ["subst"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    mappings: dict[str, Path] = {}

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if "=>" not in line:
            continue
        drive_part, target_part = (part.strip() for part in line.split("=>", 1))
        drive = drive_part.replace("\\", "")
        if len(drive) != 2 or not drive.endswith(":"):
            continue
        mappings[drive.upper()] = Path(target_part)

    return mappings


def _ensure_ascii_workspace_root(real_root: Path) -> Path:
    real_root = real_root.resolve()
    if not _contains_non_ascii(real_root):
        return real_root

    mappings = _list_subst_mappings()
    for drive, target in mappings.items():
        try:
            if target.resolve() == real_root:
                return Path(f"{drive}\\")
        except OSError:
            continue

    preferred_letters = "XYZWVUTSRQPONMLKJIHGFEDCB"
    for letter in preferred_letters:
        drive = f"{letter}:"
        if drive in mappings or Path(f"{drive}\\").exists():
            continue

        result = subprocess.run(
            ["subst", drive, str(real_root)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode == 0:
            return Path(f"{drive}\\")

    return real_root


def _bootstrap_docling_paths() -> tuple[Path, Path]:
    real_root = _find_workspace_root(Path(__file__).resolve())
    runtime_root = _ensure_ascii_workspace_root(real_root)
    site_packages = runtime_root / ".venv" / "Lib" / "site-packages"

    if site_packages.exists():
        site_packages_str = str(site_packages)
        if site_packages_str not in sys.path:
            sys.path.insert(0, site_packages_str)

    return real_root, runtime_root


WORKSPACE_ROOT, RUNTIME_WORKSPACE_ROOT = _bootstrap_docling_paths()


def _to_runtime_path(path: str | Path) -> Path:
    resolved = Path(path).resolve()
    if RUNTIME_WORKSPACE_ROOT != WORKSPACE_ROOT and resolved.is_relative_to(WORKSPACE_ROOT):
        return RUNTIME_WORKSPACE_ROOT / resolved.relative_to(WORKSPACE_ROOT)
    return resolved


def _to_real_path(path: str | Path) -> Path:
    resolved = Path(path).resolve()
    if RUNTIME_WORKSPACE_ROOT != WORKSPACE_ROOT and resolved.is_relative_to(RUNTIME_WORKSPACE_ROOT):
        return WORKSPACE_ROOT / resolved.relative_to(RUNTIME_WORKSPACE_ROOT)
    return resolved


def _count_pdf_pages(pdf_path: Path) -> int:
    import fitz

    with fitz.open(str(pdf_path)) as document:
        return document.page_count


def _split_pdf_into_chunks(
    pdf_path: Path,
    temp_root: Path,
    chunk_pages: int,
) -> list[dict[str, Any]]:
    import fitz

    chunk_specs: list[dict[str, Any]] = []
    with fitz.open(str(pdf_path)) as source_document:
        total_pages = source_document.page_count
        for chunk_index, start_page in enumerate(range(0, total_pages, chunk_pages), start=1):
            end_page = min(start_page + chunk_pages, total_pages)
            chunk_path = temp_root / f"chunk_{chunk_index:03d}_p{start_page + 1:04d}-{end_page:04d}.pdf"
            chunk_document = fitz.open()
            chunk_document.insert_pdf(
                source_document,
                from_page=start_page,
                to_page=end_page - 1,
            )
            chunk_document.save(str(chunk_path))
            chunk_document.close()
            chunk_specs.append(
                {
                    "chunk_index": chunk_index,
                    "page_start": start_page + 1,
                    "page_end": end_page,
                    "pdf_path": chunk_path,
                }
            )

    return chunk_specs


def _merge_markdown_chunks(markdown_chunks: list[str]) -> str:
    cleaned_chunks = [chunk.strip() for chunk in markdown_chunks if chunk and chunk.strip()]
    return "\n\n".join(cleaned_chunks)


def _combine_chunk_documents(
    document_name: str,
    origin: dict[str, Any],
    chunk_results: list[dict[str, Any]],
    total_pages: int,
) -> dict[str, Any]:
    return {
        "schema_name": "DoclingChunkedDocument",
        "version": "1.0.0",
        "name": document_name,
        "origin": origin,
        "total_pages": total_pages,
        "chunk_count": len(chunk_results),
        "chunks": chunk_results,
    }


def _build_origin_metadata(pdf_path: Path) -> dict[str, Any]:
    return {
        "mimetype": "application/pdf",
        "filename": pdf_path.name,
    }


def _extract_formula_texts(doc_dict: dict[str, Any]) -> list[str]:
    formulas: list[str] = []
    for item in doc_dict.get("texts", []):
        if not isinstance(item, dict):
            continue
        if item.get("label") != "formula":
            continue
        formula_text = str(item.get("text") or item.get("orig") or "").strip()
        if formula_text:
            formulas.append(formula_text)
    return formulas


def _inject_formula_fallbacks(markdown: str, doc_dict: dict[str, Any]) -> str:
    formulas = _extract_formula_texts(doc_dict)
    if not formulas or FORMULA_PLACEHOLDER not in markdown:
        return markdown

    formula_iter = iter(formulas)

    def replace_placeholder(_match: re.Match[str]) -> str:
        formula_text = next(formula_iter, "").strip()
        if not formula_text:
            return _match.group(0)
        return f"$$\n{formula_text}\n$$"

    return re.sub(re.escape(FORMULA_PLACEHOLDER), replace_placeholder, markdown)


def _export_markdown_with_assets(
    document: Any,
    doc_dict: dict[str, Any],
    output_path: Path,
    assets_dir_name: str = "assets",
) -> str:
    from docling_core.types.doc import ImageRefMode

    document.save_as_markdown(
        output_path,
        artifacts_dir=Path(assets_dir_name),
        image_mode=ImageRefMode.REFERENCED,
    )
    markdown = output_path.read_text(encoding="utf-8")
    markdown = _inject_formula_fallbacks(markdown, doc_dict)
    markdown = _postprocess_markdown(markdown)
    output_path.write_text(markdown, encoding="utf-8")
    return markdown


class DoclingLaptopConverter:
    def __init__(self) -> None:
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import AcceleratorOptions, PdfPipelineOptions
            from docling.document_converter import DocumentConverter, PdfFormatOption
        except Exception as exc:
            raise DoclingNotInstalledError(
                "Docling is not installed or failed to import. Run `pip install -r requirements.txt` in docling-parser-service."
            ) from exc

        threads = max(1, _env_int("DOCLING_PARSER_THREADS", 1))
        timeout_seconds = float(os.getenv("DOCLING_PARSER_TIMEOUT_SECONDS", "120") or "120")
        max_pages = _env_int("DOCLING_PARSER_MAX_PAGES", 80)
        max_file_mb = _env_int("DOCLING_PARSER_MAX_FILE_MB", 30)
        chunk_pages = max(1, _env_int("DOCLING_PARSER_CHUNK_PAGES", 2))
        image_scale = max(0.5, _env_float("DOCLING_PARSER_IMAGE_SCALE", 1.0))
        ocr_batch_size = max(1, _env_int("DOCLING_PARSER_OCR_BATCH_SIZE", 1))
        layout_batch_size = max(1, _env_int("DOCLING_PARSER_LAYOUT_BATCH_SIZE", 1))
        table_batch_size = max(1, _env_int("DOCLING_PARSER_TABLE_BATCH_SIZE", 1))
        queue_max_size = max(1, _env_int("DOCLING_PARSER_QUEUE_MAX_SIZE", 2))

        for env_name in (
            "OMP_NUM_THREADS",
            "DOCLING_NUM_THREADS",
            "MKL_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        ):
            os.environ[env_name] = str(threads)

        pipeline_options = PdfPipelineOptions()
        pipeline_options.document_timeout = timeout_seconds
        pipeline_options.enable_remote_services = False
        pipeline_options.force_backend_text = True
        pipeline_options.do_ocr = _env_bool("DOCLING_PARSER_ENABLE_OCR", False)
        pipeline_options.do_table_structure = _env_bool("DOCLING_PARSER_ENABLE_TABLES", True)
        pipeline_options.do_formula_enrichment = _env_bool("DOCLING_PARSER_ENABLE_FORMULAS", False)
        pipeline_options.do_code_enrichment = False
        pipeline_options.do_picture_description = False
        pipeline_options.do_picture_classification = False
        pipeline_options.do_chart_extraction = False
        pipeline_options.generate_page_images = False
        pipeline_options.generate_picture_images = _env_bool("DOCLING_PARSER_ENABLE_PICTURE_IMAGES", True)
        pipeline_options.generate_table_images = _env_bool("DOCLING_PARSER_ENABLE_TABLE_IMAGES", False)
        pipeline_options.generate_parsed_pages = False
        pipeline_options.images_scale = image_scale
        pipeline_options.ocr_batch_size = ocr_batch_size
        pipeline_options.layout_batch_size = layout_batch_size
        pipeline_options.table_batch_size = table_batch_size
        pipeline_options.queue_max_size = queue_max_size
        pipeline_options.accelerator_options = AcceleratorOptions(num_threads=threads, device="cpu")

        self._converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            },
        )
        self._chunk_pages = chunk_pages
        self._max_pages = max_pages
        self._max_file_size = max_file_mb * 1024 * 1024
        self.profile = {
            "threads": threads,
            "timeout_seconds": timeout_seconds,
            "max_pages": max_pages,
            "max_file_mb": max_file_mb,
            "chunk_pages": chunk_pages,
            "image_scale": image_scale,
            "ocr_batch_size": ocr_batch_size,
            "layout_batch_size": layout_batch_size,
            "table_batch_size": table_batch_size,
            "queue_max_size": queue_max_size,
            "do_ocr": bool(pipeline_options.do_ocr),
            "do_table_structure": bool(pipeline_options.do_table_structure),
            "do_formula_enrichment": bool(pipeline_options.do_formula_enrichment),
            "generate_picture_images": bool(pipeline_options.generate_picture_images),
            "generate_table_images": bool(pipeline_options.generate_table_images),
            "force_backend_text": bool(pipeline_options.force_backend_text),
            "device": "cpu",
            "workspace_root": str(WORKSPACE_ROOT),
            "runtime_workspace_root": str(RUNTIME_WORKSPACE_ROOT),
            "using_ascii_workspace_alias": RUNTIME_WORKSPACE_ROOT != WORKSPACE_ROOT,
        }

    def convert_pdf(
        self,
        pdf_path: str | Path,
        output_dir: str | Path,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Dict[str, str]:
        def emit_progress(message: str, *, phase: str, fraction: float, **extra: Any) -> None:
            normalized_fraction = max(0.0, min(1.0, float(fraction)))
            _log_progress(message)
            if progress_callback:
                progress_callback(
                    {
                        "phase": phase,
                        "fraction": normalized_fraction,
                        "message": message,
                        **extra,
                    }
                )

        pdf_path = Path(pdf_path).resolve()
        output_root = _ensure_directory(Path(output_dir).resolve())
        runtime_pdf_path = _to_runtime_path(pdf_path)
        runtime_output_root = _ensure_directory(_to_runtime_path(output_root))
        bundle_root = _ensure_directory(runtime_output_root / "paper_bundle")
        assets_root = _ensure_directory(bundle_root / "assets")
        total_pages = _count_pdf_pages(runtime_pdf_path)

        emit_progress(
            f"starting conversion for '{pdf_path.name}' ({total_pages} pages, chunk_pages={self._chunk_pages})",
            phase="preparing",
            fraction=0.05,
        )

        if total_pages > self._chunk_pages:
            with tempfile.TemporaryDirectory(dir=str(runtime_output_root), prefix="docling_chunks_") as chunk_dir:
                chunk_specs = _split_pdf_into_chunks(
                    runtime_pdf_path,
                    Path(chunk_dir),
                    self._chunk_pages,
                )
                chunk_markdowns: list[str] = []
                chunk_documents: list[dict[str, Any]] = []
                status_values: list[str] = []
                origin = _build_origin_metadata(pdf_path)
                document_name = pdf_path.stem
                total_chunks = max(1, len(chunk_specs))

                emit_progress(
                    f"prepared {total_chunks} chunks for docling conversion",
                    phase="preparing",
                    fraction=0.1,
                    current_chunk=0,
                    total_chunks=total_chunks,
                    page_start=1,
                    page_end=total_pages,
                )

                for chunk_spec in chunk_specs:
                    emit_progress(
                        "processing chunk "
                        f"{chunk_spec['chunk_index']}/{len(chunk_specs)} "
                        f"(pages {chunk_spec['page_start']}-{chunk_spec['page_end']})",
                        phase="parsing",
                        fraction=0.12
                        + ((chunk_spec["chunk_index"] - 1) / total_chunks) * 0.72,
                        current_chunk=chunk_spec["chunk_index"],
                        total_chunks=total_chunks,
                        page_start=chunk_spec["page_start"],
                        page_end=chunk_spec["page_end"],
                    )
                    chunk_result = self._converter.convert(
                        chunk_spec["pdf_path"],
                        raises_on_error=True,
                        max_num_pages=self._chunk_pages,
                        max_file_size=self._max_file_size,
                    )
                    chunk_document = chunk_result.document
                    chunk_document_dict = chunk_document.export_to_dict()
                    chunk_markdown_path = bundle_root / f"_chunk_{chunk_spec['chunk_index']:03d}.md"
                    chunk_markdowns.append(
                        _export_markdown_with_assets(
                            chunk_document,
                            chunk_document_dict,
                            chunk_markdown_path,
                        )
                    )
                    chunk_markdown_path.unlink(missing_ok=True)
                    document_name = str(chunk_document_dict.get("name") or document_name)
                    status_values.append(str(getattr(chunk_result, "status", "SUCCESS")))
                    chunk_documents.append(
                        {
                            "chunk_index": chunk_spec["chunk_index"],
                            "page_start": chunk_spec["page_start"],
                            "page_end": chunk_spec["page_end"],
                            "status": str(getattr(chunk_result, "status", "SUCCESS")),
                            "document": chunk_document_dict,
                        }
                    )
                    emit_progress(
                        "finished chunk "
                        f"{chunk_spec['chunk_index']}/{len(chunk_specs)} "
                        f"(pages {chunk_spec['page_start']}-{chunk_spec['page_end']}, "
                        f"status={getattr(chunk_result, 'status', 'SUCCESS')})",
                        phase="parsing",
                        fraction=0.12 + (chunk_spec["chunk_index"] / total_chunks) * 0.72,
                        current_chunk=chunk_spec["chunk_index"],
                        total_chunks=total_chunks,
                        page_start=chunk_spec["page_start"],
                        page_end=chunk_spec["page_end"],
                    )

                markdown = _merge_markdown_chunks(chunk_markdowns)
                document_dict = _combine_chunk_documents(
                    document_name=document_name,
                    origin=origin,
                    chunk_results=chunk_documents,
                    total_pages=total_pages,
                )
                markdown = _recover_chunk_boundary_sections(markdown, document_dict, assets_root)
                markdown = _postprocess_markdown(markdown)
                markdown = _inject_missing_figure_images(markdown, document_dict, _to_real_path(pdf_path), assets_root)
                status = "SUCCESS" if all(value.endswith("SUCCESS") for value in status_values) else "PARTIAL_SUCCESS"
                emit_progress(
                    f"merged {len(chunk_specs)} chunks into final bundle (status={status})",
                    phase="merging",
                    fraction=0.92,
                    current_chunk=total_chunks,
                    total_chunks=total_chunks,
                    page_start=1,
                    page_end=total_pages,
                )
        else:
            emit_progress(
                "processing single chunk document",
                phase="parsing",
                fraction=0.2,
                current_chunk=1,
                total_chunks=1,
                page_start=1,
                page_end=total_pages,
            )
            result = self._converter.convert(
                runtime_pdf_path,
                raises_on_error=True,
                max_num_pages=self._max_pages,
                max_file_size=self._max_file_size,
            )
            document = result.document
            document_dict = document.export_to_dict()
            markdown = _export_markdown_with_assets(document, document_dict, bundle_root / "paper.md")
            markdown = _postprocess_markdown(markdown)
            markdown = _inject_missing_figure_images(markdown, document_dict, _to_real_path(pdf_path), assets_root)
            status = str(getattr(result, "status", "SUCCESS"))
            emit_progress(
                f"finished single chunk document (status={status})",
                phase="parsing",
                fraction=0.88,
                current_chunk=1,
                total_chunks=1,
                page_start=1,
                page_end=total_pages,
            )

        markdown_path = bundle_root / "paper.md"
        paper_meta_path = bundle_root / "paper_meta.json"
        docling_document_path = bundle_root / "docling_document.json"

        if not markdown_path.exists():
            markdown_path.write_text(markdown, encoding="utf-8")
        docling_document_path.write_text(json.dumps(document_dict, ensure_ascii=False, indent=2), encoding="utf-8")

        paper_meta = self._build_paper_meta(
            pdf_path=pdf_path,
            doc_dict=document_dict,
            docling_document_path=_to_real_path(docling_document_path),
            assets_root=_to_real_path(assets_root),
            status=status,
            total_pages=total_pages,
        )
        paper_meta_path.write_text(json.dumps(paper_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        emit_progress(
            f"wrote paper bundle to '{_to_real_path(bundle_root)}'",
            phase="writing",
            fraction=0.97,
            page_start=1,
            page_end=total_pages,
        )

        return {
            "bundle_dir": str(_to_real_path(bundle_root)),
            "markdown_path": str(_to_real_path(markdown_path)),
            "paper_meta_path": str(_to_real_path(paper_meta_path)),
            "docling_document_path": str(_to_real_path(docling_document_path)),
        }

    def _build_paper_meta(
        self,
        pdf_path: Path,
        doc_dict: Dict[str, Any],
        docling_document_path: Path,
        assets_root: Path,
        status: str,
        total_pages: int,
    ) -> Dict[str, Any]:
        name = str(doc_dict.get("name") or pdf_path.stem)
        origin = doc_dict.get("origin", {}) if isinstance(doc_dict.get("origin"), dict) else {}
        furniture = doc_dict.get("furniture", {}) if isinstance(doc_dict.get("furniture"), dict) else {}
        body = doc_dict.get("body", {}) if isinstance(doc_dict.get("body"), dict) else {}
        groups = doc_dict.get("groups", []) if isinstance(doc_dict.get("groups"), list) else []
        texts = doc_dict.get("texts", []) if isinstance(doc_dict.get("texts"), list) else []
        chunks = doc_dict.get("chunks", []) if isinstance(doc_dict.get("chunks"), list) else []

        if chunks:
            group_count = 0
            text_item_count = 0
            has_body = False
            has_furniture = False
            for chunk in chunks:
                chunk_document = chunk.get("document", {}) if isinstance(chunk.get("document"), dict) else {}
                chunk_groups = chunk_document.get("groups", []) if isinstance(chunk_document.get("groups"), list) else []
                chunk_texts = chunk_document.get("texts", []) if isinstance(chunk_document.get("texts"), list) else []
                group_count += len(chunk_groups)
                text_item_count += len(chunk_texts)
                has_body = has_body or bool(chunk_document.get("body"))
                has_furniture = has_furniture or bool(chunk_document.get("furniture"))
        else:
            group_count = len(groups)
            text_item_count = len(texts)
            has_body = bool(body)
            has_furniture = bool(furniture)

        return {
            "doc_id": name,
            "source_pdf": str(pdf_path.resolve()),
            "parser": "docling",
            "parser_version": "docling_laptop_v1",
            "status": status,
            "total_pages": total_pages,
            "chunk_count": len(chunks) if chunks else 1,
            "profile": dict(self.profile),
            "summary": {
                "group_count": group_count,
                "text_item_count": text_item_count,
                "has_body": has_body,
                "has_furniture": has_furniture,
            },
            "artifacts": {
                "docling_document_path": str(docling_document_path.resolve()),
                "assets_dir": str(assets_root.resolve()),
            },
            "origin": origin,
        }
