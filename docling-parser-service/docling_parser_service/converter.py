from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


class DoclingNotInstalledError(RuntimeError):
    pass


FORMULA_PLACEHOLDER = "<!-- formula-not-decoded -->"


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
        chunk_pages = max(1, _env_int("DOCLING_PARSER_CHUNK_PAGES", 4))
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

    def convert_pdf(self, pdf_path: str | Path, output_dir: str | Path) -> Dict[str, str]:
        pdf_path = Path(pdf_path).resolve()
        output_root = _ensure_directory(Path(output_dir).resolve())
        runtime_pdf_path = _to_runtime_path(pdf_path)
        runtime_output_root = _ensure_directory(_to_runtime_path(output_root))
        bundle_root = _ensure_directory(runtime_output_root / "paper_bundle")
        assets_root = _ensure_directory(bundle_root / "assets")
        total_pages = _count_pdf_pages(runtime_pdf_path)

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

                for chunk_spec in chunk_specs:
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

                markdown = _merge_markdown_chunks(chunk_markdowns)
                document_dict = _combine_chunk_documents(
                    document_name=document_name,
                    origin=origin,
                    chunk_results=chunk_documents,
                    total_pages=total_pages,
                )
                status = "SUCCESS" if all(value.endswith("SUCCESS") for value in status_values) else "PARTIAL_SUCCESS"
        else:
            result = self._converter.convert(
                runtime_pdf_path,
                raises_on_error=True,
                max_num_pages=self._max_pages,
                max_file_size=self._max_file_size,
            )
            document = result.document
            document_dict = document.export_to_dict()
            markdown = _export_markdown_with_assets(document, document_dict, bundle_root / "paper.md")
            status = str(getattr(result, "status", "SUCCESS"))

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
