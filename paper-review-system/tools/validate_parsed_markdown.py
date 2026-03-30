from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def validate(markdown_text: str, meta: dict) -> list[str]:
    errors: list[str] = []

    if not re.search(r"\[Page \d+\]", markdown_text):
        errors.append("缺少 [Page x] 页面标记。")

    if not re.search(r"\[Anchor: [^\]]+\]", markdown_text):
        errors.append("缺少 [Anchor: ...] 段落锚点。")

    figure_refs = re.findall(r"\[FigureRef: [^\]]+\]", markdown_text)
    if figure_refs and "- image_path:" not in markdown_text:
        errors.append("存在 FigureRef，但缺少 image_path 字段。")

    table_refs = re.findall(r"\[TableRef: [^\]]+\]", markdown_text)
    if table_refs and "- table_path:" not in markdown_text:
        errors.append("存在 TableRef，但缺少 table_path 字段。")
    if table_refs and not re.search(r"^\|.+\|$", markdown_text, flags=re.MULTILINE):
        errors.append("存在 TableRef，但没有检测到 markdown 表格结构。")

    anchors = meta.get("anchors")
    if not isinstance(anchors, list) or not anchors:
        errors.append("paper_meta.json 中缺少可读的 anchors 数组。")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate parsed markdown against v1 spec.")
    parser.add_argument("--md", type=Path, required=True, help="Path to paper.md")
    parser.add_argument("--meta", type=Path, required=True, help="Path to paper_meta.json")
    args = parser.parse_args()

    markdown_text = args.md.read_text(encoding="utf-8")
    meta = json.loads(args.meta.read_text(encoding="utf-8"))
    errors = validate(markdown_text, meta)

    if errors:
        print("校验失败:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("校验通过: 输出符合解析规范v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
