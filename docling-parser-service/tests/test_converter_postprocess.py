from __future__ import annotations

import unittest

from docling_parser_service.converter import _postprocess_markdown


def _section_header(title: str, *, page: int, top: float, left: float = 80.0) -> dict:
    return {
        "label": "section_header",
        "text": title,
        "orig": title,
        "prov": [
            {
                "page_no": page,
                "bbox": {
                    "l": left,
                    "t": top,
                    "r": left + 100,
                    "b": top - 12,
                    "coord_origin": "BOTTOMLEFT",
                },
            }
        ],
    }


class ConverterPostprocessTests(unittest.TestCase):
    def test_explicit_blank_lines_are_preserved(self) -> None:
        markdown = """## 1.3.2 仓库级代码智能任务
第一行没有句号 仍然属于同一段

另一段重新开始 也应继续保留
"""

        processed = _postprocess_markdown(markdown)

        self.assertIn("第一行没有句号仍然属于同一段", processed)
        self.assertIn("\n\n另一段重新开始也应继续保留\n", processed)

    def test_chapter_intro_stays_with_chapter_heading(self) -> None:
        markdown = """## 第二章 仓库级增量代码生成相关理论与技术
这是第二章的引言段。
## 2.1 仓库级增量代码生成
这里是 2.1 的正文。
"""

        processed = _postprocess_markdown(markdown)

        self.assertIn("## 第二章 仓库级增量代码生成相关理论与技术\n这是第二章的引言段。", processed)
        self.assertIn("## 2.1 仓库级增量代码生成\n这里是 2.1 的正文。", processed)

    def test_first_child_body_chapter_intro_is_hoisted_back_to_chapter(self) -> None:
        markdown = """## 第二章 仓库级增量代码生成相关理论与技术
## 2.1 仓库级增量代码生成
这是一段应回到第二章标题下的章节引导，本章将进行详细介绍。

这里是 2.1 的正文。
"""

        processed = _postprocess_markdown(markdown)

        self.assertIn(
            "## 第二章 仓库级增量代码生成相关理论与技术\n这是一段应回到第二章标题下的章节引导，本章将进行详细介绍。",
            processed,
        )
        self.assertIn("## 2.1 仓库级增量代码生成\n这里是 2.1 的正文。", processed)
        self.assertEqual(processed.count("本章将进行详细介绍。"), 1)

    def test_table_block_gets_trailing_blank_line(self) -> None:
        markdown = """## 3.2.2 程序员推理路径数据标注
表 2 初始 RPU 集合分类
| 类别 | RPU 名称 |
| --- | --- |
| A | B |
表后正文
"""

        processed = _postprocess_markdown(markdown)

        self.assertIn("| A | B |\n\n表后正文", processed)

    def test_image_block_gets_trailing_blank_line(self) -> None:
        markdown = """## 2.2.5 AI Agent 技术
图 4 AI Agent 结构示意图
![Image](assets/example.png)
图后正文
"""

        processed = _postprocess_markdown(markdown)

        self.assertIn("![Image](assets/example.png)\n\n图后正文", processed)

    def test_adjacent_plain_text_lines_become_distinct_paragraphs(self) -> None:
        markdown = """## 2.2.1 代码生成模型
第一段内容。
第二段内容。
第三段内容。
"""

        processed = _postprocess_markdown(markdown)

        self.assertIn("第一段内容。\n\n第二段内容。\n\n第三段内容。", processed)

    def test_algorithm_like_headings_are_demoted_into_body(self) -> None:
        markdown = """## 3.2.5 推理图 GoR 合成
本节导语。
## 算法：GoR
错误! 未找到引用源。
## Synthesis
输入: 数据集
## 输出：GoR G
10. return G
## 表 3 CodeBrain 推理过程算法伪代码
## 4.1 CodeBrain 整体流程
这里是后续章节。
"""

        processed = _postprocess_markdown(markdown)

        self.assertIn("表 3 CodeBrain 推理过程算法伪代码", processed)
        self.assertIn("算法：GoR", processed)
        self.assertIn("Synthesis", processed)
        self.assertIn("输出：GoR G", processed)
        self.assertNotIn("\n## 算法：GoR\n", processed)
        self.assertNotIn("\n## Synthesis\n", processed)
        self.assertNotIn("\n## 输出：GoR G\n", processed)
        self.assertNotIn("\n## 表 3 CodeBrain 推理过程算法伪代码\n", processed)
        self.assertIn("## 4.1 CodeBrain 整体流程\n这里是后续章节。", processed)

    def test_feature_analysis_fragment_is_repaired(self) -> None:
        markdown = """## 4.2.2 功能分析智能体
Structure  Feature 。该过程基于 LLM 实现，通过设计提示模板将输入的新功能需求转化为包含关键信息的结构化需求形式。

实现。首先提取需求中提取与实现新功能相

Analyse Webpage Content 。该过程基于网络请求接口与 LLM 的网页链接；然后基于网络请求接口提取相关内容；最后由 LLM 关的内容。
"""

        processed = _postprocess_markdown(markdown)

        self.assertIn("Structure Feature 。该过程基于 LLM 实现", processed)
        self.assertIn(
            "Analyse Webpage Content 。该过程基于网络请求接口与 LLM 实现。首先提取需求中的网页链接；然后基于网络请求接口提取相关内容；最后由 LLM 提取与实现新功能相关的内容。",
            processed,
        )
        self.assertNotIn("实现。首先提取需求中提取与实现新功能相", processed)
        self.assertNotIn("该过程基于网络请求接口与 LLM 的网页链接", processed)

    def test_duplicate_sibling_section_numbers_are_renumbered(self) -> None:
        markdown = """## 4.2 各组件设计说明
## 4.2.1 决策智能体
决策正文
## 4.2.1 功能分析智能体
功能分析正文
## 4.2.1 代码定位智能体
代码定位正文
"""

        processed = _postprocess_markdown(markdown)

        self.assertIn("## 4.2.1 决策智能体", processed)
        self.assertIn("## 4.2.2 功能分析智能体", processed)
        self.assertIn("## 4.2.3 代码定位智能体", processed)


    def test_parenthesized_chinese_section_headings_become_level_three(self) -> None:
        markdown = (
            "## 4.2 \u5404\u7ec4\u4ef6\u8bbe\u8ba1\u8bf4\u660e\n"
            "## \uff08\u4e00\uff09\u529f\u80fd\u5206\u6790\u667a\u80fd\u4f53\n"
            "\u8fd9\u91cc\u662f\u6b63\u6587\u3002\n"
        )

        processed = _postprocess_markdown(markdown)

        self.assertIn("## 4.2 \u5404\u7ec4\u4ef6\u8bbe\u8ba1\u8bf4\u660e", processed)
        self.assertIn("### \uff08\u4e00\uff09\u529f\u80fd\u5206\u6790\u667a\u80fd\u4f53", processed)
        self.assertNotIn("\n## \uff08\u4e00\uff09\u529f\u80fd\u5206\u6790\u667a\u80fd\u4f53\n", processed)

    def test_compatibility_ideographs_in_titles_are_normalized(self) -> None:
        markdown = (
            "## 4.2 \u5404\u7ec4\u4ef6\u8bbe\u8ba1\u8bf4\u660e\n"
            "## \uff08\u2f00\uff09\u529f\u80fd\u5206\u6790\u667a\u80fd\u4f53\n"
            "\u5e94\u2f64\u573a\u666f\u8bf4\u660e\u3002\n"
        )

        processed = _postprocess_markdown(markdown)

        self.assertIn("### \uff08\u4e00\uff09\u529f\u80fd\u5206\u6790\u667a\u80fd\u4f53", processed)
        self.assertIn("\u5e94\u7528\u573a\u666f\u8bf4\u660e\u3002", processed)
        self.assertNotIn("\u2f00", processed)
        self.assertNotIn("\u2f64", processed)

    def test_related_work_children_misordered_after_abstract_are_moved_under_related_work(self) -> None:
        markdown = (
            "## \u6458\u8981\n"
            "\u6458\u8981\u6b63\u6587\u3002\n"
            "## \uff08\u4e00\uff09\u56fd\u5185\u7814\u7a76\u73b0\u72b6\n"
            "\u56fd\u5185\u7814\u7a76\u6b63\u6587\u3002\n"
            "## \uff08\u4e8c\uff09\u52a8\u673a\u4e0e\u89c2\u5bdf\n"
            "\u52a8\u673a\u6b63\u6587\u3002\n"
            "## \u4e00\u3001\u5f15\u8a00\n"
            "\u5f15\u8a00\u6b63\u6587\u3002\n"
            "## \u4e8c\u3001\u76f8\u5173\u7814\u7a76\n"
            "\u76f8\u5173\u7814\u7a76\u5bfc\u8bed\u3002\n"
            "## \u4e09\u3001\u7814\u7a76\u65b9\u6cd5\n"
            "\u65b9\u6cd5\u6b63\u6587\u3002\n"
        )

        processed = _postprocess_markdown(markdown)

        abstract_index = processed.index("## \u6458\u8981")
        intro_index = processed.index("## \u4e00\u3001\u5f15\u8a00")
        related_index = processed.index("## \u4e8c\u3001\u76f8\u5173\u7814\u7a76")
        domestic_index = processed.index("### \uff08\u4e00\uff09\u56fd\u5185\u7814\u7a76\u73b0\u72b6")
        motivation_index = processed.index("### \uff08\u4e8c\uff09\u52a8\u673a\u4e0e\u89c2\u5bdf")
        method_index = processed.index("## \u4e09\u3001\u7814\u7a76\u65b9\u6cd5")

        self.assertLess(abstract_index, intro_index)
        self.assertLess(intro_index, related_index)
        self.assertLess(related_index, domestic_index)
        self.assertLess(domestic_index, motivation_index)
        self.assertLess(motivation_index, method_index)

    def test_single_arabic_headings_after_chinese_chapter_are_demoted(self) -> None:
        markdown = (
            "## \u4e09\u3001\u7814\u7a76\u8bbe\u8ba1\u4e0e\u65b9\u6cd5\n"
            "## \uff08\u4e00\uff09\u6570\u636e\u6765\u6e90\n"
            "\u6570\u636e\u6b63\u6587\u3002\n"
            "## 1. \u6a21\u578b\u6784\u5efa\n"
            "\u6a21\u578b\u6b63\u6587\u3002\n"
            "## 2. \u8bc4\u4ef7\u6307\u6807\n"
            "\u6307\u6807\u6b63\u6587\u3002\n"
        )

        processed = _postprocess_markdown(markdown)

        self.assertIn("### 1. \u6a21\u578b\u6784\u5efa", processed)
        self.assertIn("### 2. \u8bc4\u4ef7\u6307\u6807", processed)
        self.assertNotIn("\n## 1. \u6a21\u578b\u6784\u5efa\n", processed)
        self.assertNotIn("\n## 2. \u8bc4\u4ef7\u6307\u6807\n", processed)

    def test_bbox_repair_reorders_same_page_heading_inversion(self) -> None:
        markdown = (
            "## \u6458\u8981\n"
            "\u6458\u8981\u6b63\u6587\u3002\n"
            "## \uff08\u4e00\uff09\u8bef\u6392\u5c0f\u8282\n"
            "\u8bef\u6392\u6b63\u6587\u3002\n"
            "## \u4e00\u3001\u5f15\u8a00\n"
            "\u5f15\u8a00\u6b63\u6587\u3002\n"
            "## \uff08\u4e00\uff09\u7814\u7a76\u80cc\u666f\n"
            "\u80cc\u666f\u6b63\u6587\u3002\n"
        )
        doc_dict = {
            "chunks": [
                {
                    "page_start": 1,
                    "document": {
                        "texts": [
                            _section_header("\u6458\u8981", page=1, top=760),
                            _section_header("\uff08\u4e00\uff09\u8bef\u6392\u5c0f\u8282", page=2, top=280),
                            _section_header("\u4e00\u3001\u5f15\u8a00", page=2, top=740),
                            _section_header("\uff08\u4e00\uff09\u7814\u7a76\u80cc\u666f", page=2, top=620),
                        ]
                    },
                }
            ]
        }

        processed = _postprocess_markdown(markdown, doc_dict=doc_dict)

        intro_index = processed.index("## \u4e00\u3001\u5f15\u8a00")
        background_index = processed.index("### \uff08\u4e00\uff09\u7814\u7a76\u80cc\u666f")
        misplaced_index = processed.index("### \uff08\u4e00\uff09\u8bef\u6392\u5c0f\u8282")
        self.assertLess(intro_index, background_index)
        self.assertLess(background_index, misplaced_index)

    def test_bbox_repair_keeps_cross_page_order(self) -> None:
        markdown = (
            "## \u4e00\u3001\u7b2c\u4e00\u9875\u7ae0\u8282\n"
            "\u7b2c\u4e00\u9875\u6b63\u6587\u3002\n"
            "## \u4e8c\u3001\u7b2c\u4e8c\u9875\u7ae0\u8282\n"
            "\u7b2c\u4e8c\u9875\u6b63\u6587\u3002\n"
        )
        doc_dict = {
            "texts": [
                _section_header("\u4e00\u3001\u7b2c\u4e00\u9875\u7ae0\u8282", page=1, top=120),
                _section_header("\u4e8c\u3001\u7b2c\u4e8c\u9875\u7ae0\u8282", page=2, top=760),
            ]
        }

        processed = _postprocess_markdown(markdown, doc_dict=doc_dict)

        self.assertLess(
            processed.index("## \u4e00\u3001\u7b2c\u4e00\u9875\u7ae0\u8282"),
            processed.index("## \u4e8c\u3001\u7b2c\u4e8c\u9875\u7ae0\u8282"),
        )

    def test_bbox_repair_is_noop_without_docling_metadata(self) -> None:
        markdown = (
            "## \uff08\u4e00\uff09\u8bef\u6392\u5c0f\u8282\n"
            "\u8bef\u6392\u6b63\u6587\u3002\n"
            "## \u4e00\u3001\u5f15\u8a00\n"
            "\u5f15\u8a00\u6b63\u6587\u3002\n"
        )

        processed = _postprocess_markdown(markdown)

        self.assertLess(
            processed.index("### \uff08\u4e00\uff09\u8bef\u6392\u5c0f\u8282"),
            processed.index("## \u4e00\u3001\u5f15\u8a00"),
        )


if __name__ == "__main__":
    unittest.main()
