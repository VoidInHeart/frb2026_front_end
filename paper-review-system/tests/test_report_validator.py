from __future__ import annotations

import unittest

from paper_review_system.models import PageInfo, PaperBlock, PaperDocument
from paper_review_system.report.validator import ReportValidator


class ReportValidatorTest(unittest.TestCase):
    def test_validate_accepts_empty_arrays(self) -> None:
        payload = {
            "project_metadata": {},
            "logic_analysis": {"core_argument_consistency": {"details": []}},
            "rule_violations": [],
            "improvement_plan": {"semantic_refinement": [], "expert_samples": []},
        }
        ReportValidator().validate(payload)

    def test_validate_rejects_duplicate_ids(self) -> None:
        payload = {
            "project_metadata": {},
            "logic_analysis": {"core_argument_consistency": {"details": []}},
            "rule_violations": [{"id": "R-FMT-001"}, {"id": "R-FMT-001"}],
            "improvement_plan": {"semantic_refinement": [], "expert_samples": []},
        }
        with self.assertRaises(ValueError):
            ReportValidator().validate(payload)

    def test_document_to_dict_supports_slotted_pages(self) -> None:
        document = PaperDocument(
            doc_id="demo",
            source_file="demo.pdf",
            pages=[PageInfo(page=1, width=595.0, height=842.0)],
            blocks=[PaperBlock(block_id="blk_1", page=1, bbox=[0, 0, 10, 10], type="paragraph", text="正文")],
        )
        payload = document.to_dict()
        self.assertEqual(payload["pages"][0]["page"], 1)
        self.assertEqual(payload["blocks"][0]["text"], "正文")


if __name__ == "__main__":
    unittest.main()
