from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


class DoclingNotInstalledError(RuntimeError):
    pass


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


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

        threads = _env_int("DOCLING_PARSER_THREADS", 4)
        timeout_seconds = float(os.getenv("DOCLING_PARSER_TIMEOUT_SECONDS", "120") or "120")
        max_pages = _env_int("DOCLING_PARSER_MAX_PAGES", 80)
        max_file_mb = _env_int("DOCLING_PARSER_MAX_FILE_MB", 30)

        os.environ.setdefault("OMP_NUM_THREADS", str(threads))
        os.environ.setdefault("DOCLING_NUM_THREADS", str(threads))

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
        pipeline_options.generate_picture_images = _env_bool("DOCLING_PARSER_ENABLE_PICTURE_IMAGES", False)
        pipeline_options.generate_table_images = _env_bool("DOCLING_PARSER_ENABLE_TABLE_IMAGES", False)
        pipeline_options.generate_parsed_pages = False
        pipeline_options.accelerator_options = AcceleratorOptions(num_threads=threads, device="cpu")

        self._converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            },
        )
        self._max_pages = max_pages
        self._max_file_size = max_file_mb * 1024 * 1024
        self.profile = {
            "threads": threads,
            "timeout_seconds": timeout_seconds,
            "max_pages": max_pages,
            "max_file_mb": max_file_mb,
            "do_ocr": bool(pipeline_options.do_ocr),
            "do_table_structure": bool(pipeline_options.do_table_structure),
            "do_formula_enrichment": bool(pipeline_options.do_formula_enrichment),
            "generate_picture_images": bool(pipeline_options.generate_picture_images),
            "generate_table_images": bool(pipeline_options.generate_table_images),
            "force_backend_text": bool(pipeline_options.force_backend_text),
            "device": "cpu",
        }

    def convert_pdf(self, pdf_path: str | Path, output_dir: str | Path) -> Dict[str, str]:
        pdf_path = Path(pdf_path)
        output_root = _ensure_directory(Path(output_dir))
        bundle_root = _ensure_directory(output_root / "paper_bundle")
        assets_root = _ensure_directory(bundle_root / "assets")

        result = self._converter.convert(
            pdf_path,
            raises_on_error=True,
            max_num_pages=self._max_pages,
            max_file_size=self._max_file_size,
        )
        document = result.document
        markdown = document.export_to_markdown()
        document_dict = document.export_to_dict()

        markdown_path = bundle_root / "paper.md"
        paper_meta_path = bundle_root / "paper_meta.json"
        docling_document_path = bundle_root / "docling_document.json"

        markdown_path.write_text(markdown, encoding="utf-8")
        docling_document_path.write_text(json.dumps(document_dict, ensure_ascii=False, indent=2), encoding="utf-8")

        paper_meta = self._build_paper_meta(
            pdf_path=pdf_path,
            doc_dict=document_dict,
            docling_document_path=docling_document_path,
            assets_root=assets_root,
            status=str(getattr(result, "status", "SUCCESS")),
        )
        paper_meta_path.write_text(json.dumps(paper_meta, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "bundle_dir": str(bundle_root.resolve()),
            "markdown_path": str(markdown_path.resolve()),
            "paper_meta_path": str(paper_meta_path.resolve()),
            "docling_document_path": str(docling_document_path.resolve()),
        }

    def _build_paper_meta(
        self,
        pdf_path: Path,
        doc_dict: Dict[str, Any],
        docling_document_path: Path,
        assets_root: Path,
        status: str,
    ) -> Dict[str, Any]:
        name = str(doc_dict.get("name") or pdf_path.stem)
        origin = doc_dict.get("origin", {}) if isinstance(doc_dict.get("origin"), dict) else {}
        furniture = doc_dict.get("furniture", {}) if isinstance(doc_dict.get("furniture"), dict) else {}
        body = doc_dict.get("body", {}) if isinstance(doc_dict.get("body"), dict) else {}
        groups = doc_dict.get("groups", []) if isinstance(doc_dict.get("groups"), list) else []
        texts = doc_dict.get("texts", []) if isinstance(doc_dict.get("texts"), list) else []

        return {
            "doc_id": name,
            "source_pdf": str(pdf_path.resolve()),
            "parser": "docling",
            "parser_version": "docling_laptop_v1",
            "status": status,
            "profile": dict(self.profile),
            "summary": {
                "group_count": len(groups),
                "text_item_count": len(texts),
                "has_body": bool(body),
                "has_furniture": bool(furniture),
            },
            "artifacts": {
                "docling_document_path": str(docling_document_path.resolve()),
                "assets_dir": str(assets_root.resolve()),
            },
            "origin": origin,
        }
