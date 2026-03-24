from __future__ import annotations

import unittest

from paper_review_system.models import PaperBlock
from paper_review_system.parser.markdown_renderer import MarkdownRenderer
from paper_review_system.parser.pdf_parser import PDFParser
from paper_review_system.rules.grammar_rules import GrammarRuleChecker
from paper_review_system.rules.violation_id import ViolationIdAllocator


class MarkdownRendererTest(unittest.TestCase):
    def test_render_skips_noise_and_formats_headings(self) -> None:
        blocks = [
            PaperBlock(block_id="1", page=1, bbox=[0, 0, 1, 1], type="heading", text="摘要", level=2),
            PaperBlock(block_id="2", page=1, bbox=[0, 0, 1, 1], type="paragraph", text="这是正文。"),
            PaperBlock(block_id="3", page=1, bbox=[0, 0, 1, 1], type="paragraph", text="页码", is_noise=True),
        ]
        markdown = MarkdownRenderer().render(blocks)
        self.assertIn("## 摘要", markdown)
        self.assertIn("这是正文。", markdown)
        self.assertNotIn("页码", markdown)

    def test_render_formats_captions_as_quotes(self) -> None:
        blocks = [PaperBlock(block_id="1", page=1, bbox=[0, 0, 1, 1], type="caption", text="Figure 1. Demo caption")]
        markdown = MarkdownRenderer().render(blocks)
        self.assertIn("> Figure 1. Demo caption", markdown)

    def test_pdf_text_normalization_merges_hyphenated_lines(self) -> None:
        text = "diffu-\nsion 鈥?driven"
        normalized = PDFParser._normalize_text(text)
        self.assertEqual(normalized, "diffusion -driven")

    def test_grammar_checker_skips_caption_like_blocks(self) -> None:
        blocks = [
            PaperBlock(
                block_id="1",
                page=1,
                bbox=[0, 0, 1, 1],
                type="paragraph",
                text="Figure 1. " + ("caption " * 60),
                role="caption",
            )
        ]
        violations = GrammarRuleChecker().check(blocks, ViolationIdAllocator())
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
