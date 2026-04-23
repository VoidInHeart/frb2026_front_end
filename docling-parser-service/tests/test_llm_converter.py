from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

import fitz

from docling_parser_service.llm_converter import OpenAICompatiblePdfConverter


def _make_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Test Paper\nIntroduction\nMethod\nReferences")
    path.write_bytes(document.tobytes())
    document.close()


class LlmConverterTests(unittest.TestCase):
    def test_dashscope_requires_document_model(self) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "qwen-long|qwen-doc-turbo",
        ):
            OpenAICompatiblePdfConverter(
                api_key="test-key",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model="qwen3.6-flash",
            )

    def test_openai_compatible_converter_writes_bundle_and_meta(self) -> None:
        captured: dict[str, object] = {}

        def fake_request(
            endpoint: str,
            headers: dict[str, str],
            body: dict[str, object],
            timeout_seconds: float,
        ) -> dict[str, object]:
            captured["endpoint"] = endpoint
            captured["headers"] = headers
            captured["body"] = body
            captured["timeout_seconds"] = timeout_seconds
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "Test Paper",
                                    "abstract": "Short abstract.",
                                    "paper_markdown": (
                                        "# Test Paper\n\n"
                                        "## Introduction\n"
                                        "This is the introduction.\n\n"
                                        "## Method\n"
                                        "> Figure 1. Overall pipeline.\n"
                                        "> Visual summary: A pipeline diagram.\n\n"
                                        "| Model | Score |\n"
                                        "| --- | --- |\n"
                                        "| Ours | 0.91 |\n\n"
                                        "## References\n"
                                        "- [1] Example reference without terminal punctuation\n"
                                    ),
                                    "sections": [
                                        {"section_title": "Introduction", "page_no": 1},
                                        {"section_title": "Method", "page_no": 1},
                                        {"section_title": "References", "page_no": 1},
                                    ],
                                    "figures": [
                                        {
                                            "id": "fig_001",
                                            "label": "Figure 1",
                                            "caption": "Overall pipeline.",
                                            "page_no": 1,
                                            "description": "A pipeline diagram.",
                                            "section_title": "Method",
                                        }
                                    ],
                                    "tables": [
                                        {
                                            "id": "tab_001",
                                            "label": "Table 1",
                                            "caption": "Main results.",
                                            "page_no": 1,
                                            "section_title": "Method",
                                            "markdown": (
                                                "| Model | Score |\n"
                                                "| --- | --- |\n"
                                                "| Ours | 0.91 |"
                                            ),
                                        }
                                    ],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 120, "completion_tokens": 240},
            }

        sandbox_root = Path(__file__).resolve().parent / "_tmp" / "llm_converter_case"
        if sandbox_root.exists():
            shutil.rmtree(sandbox_root)
        sandbox_root.mkdir(parents=True, exist_ok=True)

        try:
            root = sandbox_root
            pdf_path = root / "sample.pdf"
            out_dir = root / "out"
            _make_pdf(pdf_path)

            converter = OpenAICompatiblePdfConverter(
                api_key="test-key",
                base_url="http://example.test/v1",
                model="gpt-test",
                request_callable=fake_request,
            )
            result = converter.convert_pdf(pdf_path, out_dir)

            self.assertTrue(str(captured["endpoint"]).endswith("/chat/completions"))
            request_body = captured["body"]
            self.assertIsInstance(request_body, dict)
            self.assertEqual(request_body.get("model"), "gpt-test")

            messages = request_body.get("messages", [])
            self.assertIsInstance(messages, list)
            user_message = messages[1]
            self.assertEqual(user_message.get("role"), "user")
            file_part = user_message.get("content", [])[1]
            self.assertEqual(file_part.get("type"), "file")

            markdown_path = Path(result["markdown_path"])
            paper_meta_path = Path(result["paper_meta_path"])
            llm_result_path = Path(result["llm_result_path"])

            self.assertTrue(markdown_path.exists())
            self.assertTrue(paper_meta_path.exists())
            self.assertTrue(llm_result_path.exists())

            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("## Method", markdown)
            self.assertIn("| Model | Score |", markdown)

            paper_meta = json.loads(paper_meta_path.read_text(encoding="utf-8"))
            self.assertEqual(paper_meta.get("parser"), "openai_compatible_llm")
            self.assertEqual(paper_meta.get("parser_version"), "openai_chat_completions_pdf_v1")
            self.assertEqual(paper_meta.get("image_count"), 1)
            self.assertTrue(any(item.get("type") == "figure" for item in paper_meta.get("anchors", [])))
            self.assertTrue(any(item.get("type") == "table" for item in paper_meta.get("anchors", [])))
            self.assertTrue(
                any(
                    item.get("type") == "missing_terminal_punctuation"
                    for item in paper_meta.get("reference_diagnostics", [])
                )
            )
        finally:
            shutil.rmtree(sandbox_root, ignore_errors=True)

    def test_dashscope_converter_uploads_file_then_uses_fileid_chat(self) -> None:
        captured: dict[str, object] = {}
        retrieve_calls = {"count": 0}
        chat_calls = {"count": 0}

        def fake_file_upload(
            endpoint: str,
            headers: dict[str, str],
            pdf_path: Path,
            timeout_seconds: float,
        ) -> dict[str, object]:
            captured["file_upload_endpoint"] = endpoint
            captured["file_upload_headers"] = headers
            captured["file_upload_path"] = str(pdf_path)
            captured["file_upload_timeout"] = timeout_seconds
            return {"id": "file-fe-test123"}

        def fake_file_retrieve(
            endpoint: str,
            headers: dict[str, str],
            timeout_seconds: float,
        ) -> dict[str, object]:
            retrieve_calls["count"] += 1
            captured["file_retrieve_endpoint"] = endpoint
            if retrieve_calls["count"] < 2:
                return {"id": "file-fe-test123", "status": "processing"}
            return {"id": "file-fe-test123", "status": "processed"}

        def fake_request(
            endpoint: str,
            headers: dict[str, str],
            body: dict[str, object],
            timeout_seconds: float,
        ) -> dict[str, object]:
            chat_calls["count"] += 1
            captured["chat_endpoint"] = endpoint
            captured["chat_headers"] = headers
            captured["chat_body"] = body
            captured["chat_timeout"] = timeout_seconds
            if chat_calls["count"] == 1:
                raise RuntimeError("LLM parser request failed: HTTP 400 File parsing in progress")
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "title": "DashScope Paper",
                                    "paper_markdown": "# DashScope Paper\n\n## References\n- [1] Ref.\n",
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }

        sandbox_root = Path(__file__).resolve().parent / "_tmp" / "llm_converter_dashscope_case"
        if sandbox_root.exists():
            shutil.rmtree(sandbox_root)
        sandbox_root.mkdir(parents=True, exist_ok=True)

        try:
            pdf_path = sandbox_root / "sample.pdf"
            out_dir = sandbox_root / "out"
            _make_pdf(pdf_path)

            converter = OpenAICompatiblePdfConverter(
                api_key="test-key",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                model="qwen-doc-turbo",
                request_callable=fake_request,
                file_upload_callable=fake_file_upload,
                file_retrieve_callable=fake_file_retrieve,
            )
            result = converter.convert_pdf(pdf_path, out_dir)

            self.assertEqual(
                captured["file_upload_endpoint"],
                "https://dashscope.aliyuncs.com/compatible-mode/v1/files",
            )
            self.assertEqual(
                captured["file_retrieve_endpoint"],
                "https://dashscope.aliyuncs.com/compatible-mode/v1/files/file-fe-test123",
            )
            self.assertEqual(
                captured["chat_endpoint"],
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            )
            chat_body = captured["chat_body"]
            self.assertIsInstance(chat_body, dict)
            messages = chat_body.get("messages", [])
            self.assertEqual(messages[1].get("content"), "fileid://file-fe-test123")
            self.assertEqual(messages[2].get("role"), "user")
            self.assertGreaterEqual(retrieve_calls["count"], 2)
            self.assertEqual(chat_calls["count"], 2)
            self.assertTrue(Path(result["markdown_path"]).exists())
        finally:
            shutil.rmtree(sandbox_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
