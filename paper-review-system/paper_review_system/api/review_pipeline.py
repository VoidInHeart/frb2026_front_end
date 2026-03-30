from __future__ import annotations

import csv
import json
import re
from collections import defaultdict, deque
from pathlib import Path

from paper_review_system.io_utils import ensure_directory, write_json, write_text
from paper_review_system.models import EvidenceBundle, PaperBlock, PaperDocument, SectionNode
from paper_review_system.parser.anchor_builder import AnchorBuilder
from paper_review_system.parser.markdown_renderer import MarkdownRenderer
from paper_review_system.parser.noise_cleaner import NoiseCleaner
from paper_review_system.parser.pdf_parser import PDFParser
from paper_review_system.parser.section_builder import SectionTreeBuilder
from paper_review_system.parser.table_reconstructor import TableStructureRestorer


class ReviewPipeline:
    """Pipeline for PDF parsing and anchor-list bundle generation."""

    PARSER_VERSION = "v1.0.0"

    def __init__(self) -> None:
        self.pdf_parser = PDFParser()
        self.noise_cleaner = NoiseCleaner()
        self.table_reconstructor = TableStructureRestorer()
        self.section_builder = SectionTreeBuilder()
        self.anchor_builder = AnchorBuilder()
        self.markdown_renderer = MarkdownRenderer()

    def convert_pdf(self, pdf_path: str | Path, output_dir: str | Path) -> dict[str, str]:
        output_root = ensure_directory(Path(output_dir))
        bundle_root = ensure_directory(output_root / "paper_bundle")
        assets_root = ensure_directory(bundle_root / "assets")
        figures_root = ensure_directory(assets_root / "figures")
        tables_root = ensure_directory(assets_root / "tables")

        document = self.pdf_parser.parse(pdf_path)
        evidence = self._build_evidence(document)
        figure_refs = self._extract_figures(document.source_file, figures_root, evidence.clean_blocks)
        table_refs = self._export_tables(document.source_file, tables_root, evidence.clean_blocks)
        markdown, paper_meta = self._build_bundle(document, evidence, figure_refs, table_refs)

        markdown_path = bundle_root / "paper.md"
        paper_meta_path = bundle_root / "paper_meta.json"

        write_text(markdown_path, markdown)
        write_json(paper_meta_path, paper_meta)

        return {
            "bundle_dir": str(bundle_root.resolve()),
            "markdown_path": str(markdown_path.resolve()),
            "paper_meta_path": str(paper_meta_path.resolve()),
        }

    def _build_evidence(self, document: PaperDocument) -> EvidenceBundle:
        clean_blocks = self.noise_cleaner.clean(document)
        clean_blocks = self.table_reconstructor.restore(
            document.source_file,
            clean_blocks,
            document.pages,
        )
        section_tree = self.section_builder.build(clean_blocks)
        anchors = self.anchor_builder.build(clean_blocks, section_tree)
        return EvidenceBundle(
            doc_id=document.doc_id,
            anchors=anchors,
            clean_blocks=clean_blocks,
            raw_blocks=document.blocks,
            section_tree=section_tree,
        )

    def _extract_figures(
        self,
        pdf_path: str | Path,
        figures_root: Path,
        clean_blocks: list[PaperBlock],
    ) -> list[dict[str, str | int]]:
        try:
            import fitz
        except ImportError:
            return []

        caption_queues = self._build_figure_caption_queues(clean_blocks)
        refs: list[dict[str, str | int]] = []
        global_index = 0

        pdf = fitz.open(str(Path(pdf_path).resolve()))
        for page_index, page in enumerate(pdf, start=1):
            for image_index, image in enumerate(page.get_images(full=True), start=1):
                xref = image[0]
                try:
                    pix = fitz.Pixmap(pdf, xref)
                    if pix.width < 50 or pix.height < 50:
                        pix = None
                        continue

                    if pix.n > 4:
                        with fitz.Pixmap(fitz.csRGB, pix) as pix_rgb:
                            img_data = pix_rgb.tobytes("png")
                    else:
                        img_data = pix.tobytes("png")

                    pix = None
                    if not img_data:
                        continue

                    global_index += 1
                    figure_no = f"{global_index:02d}"
                    filename = f"p{page_index}_fig_{figure_no}.png"
                    image_path = figures_root / filename
                    image_path.write_bytes(img_data)

                    caption_queue = caption_queues.get(page_index, deque())
                    caption = (
                        caption_queue.popleft()
                        if caption_queue
                        else f"Figure on page {page_index}"
                    )

                    refs.append(
                        {
                            "figure_id": f"Fig_{figure_no}",
                            "anchor_id": f"P{page_index}_Fig_{figure_no}",
                            "page_no": page_index,
                            "caption": caption,
                            "image_path": f"assets/figures/{filename}",
                        }
                    )
                except Exception:
                    continue

        pdf.close()
        return refs

    def _export_tables(
        self,
        pdf_path: str | Path,
        tables_root: Path,
        clean_blocks: list[PaperBlock],
    ) -> dict[str, dict[str, str | int]]:
        try:
            import fitz
        except ImportError:
            fitz = None

        table_refs: dict[str, dict[str, str | int]] = {}
        table_blocks = [
            block
            for block in clean_blocks
            if not block.is_noise and block.type == "table"
        ]

        pdf = fitz.open(str(Path(pdf_path).resolve())) if fitz else None

        for index, block in enumerate(table_blocks, start=1):
            table_no = f"{index:02d}"
            csv_name = f"p{block.page}_tab_{table_no}.csv"
            png_name = f"p{block.page}_tab_{table_no}.png"
            csv_path = tables_root / csv_name
            png_path = tables_root / png_name

            with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                headers = list(block.table_headers or [])
                rows = [list(row) for row in (block.table_rows or [])]
                if headers:
                    writer.writerow(headers)
                writer.writerows(rows)

            if pdf is not None:
                try:
                    page = pdf.load_page(block.page - 1)
                    clip = fitz.Rect(*block.bbox)
                    clip = clip + (-8, -8, 8, 8)
                    pix = page.get_pixmap(clip=clip, matrix=fitz.Matrix(2, 2))
                    png_path.write_bytes(pix.tobytes("png"))
                except Exception:
                    png_path.write_bytes(b"")
            else:
                png_path.write_bytes(b"")

            table_refs[block.block_id] = {
                "table_id": f"Tab_{table_no}",
                "anchor_id": f"P{block.page}_Tab_{table_no}",
                "page_no": block.page,
                "caption": block.table_caption or f"Table on page {block.page}",
                "table_path": f"assets/tables/{csv_name}",
                "screenshot_path": f"assets/tables/{png_name}",
            }

        if pdf is not None:
            pdf.close()

        return table_refs

    def _build_bundle(
        self,
        document: PaperDocument,
        evidence: EvidenceBundle,
        figure_refs: list[dict[str, str | int]],
        table_refs: dict[str, dict[str, str | int]],
    ) -> tuple[str, dict]:
        section_maps = self._build_section_maps(evidence.section_tree)
        text_counters: defaultdict[tuple[int, int], int] = defaultdict(int)
        figure_refs_by_page = self._group_by_page(figure_refs)
        figure_caption_map = self._group_figure_ref_by_caption(figure_refs)

        lines: list[str] = []
        meta_anchors: list[dict] = []
        current_page = None

        for block in evidence.clean_blocks:
            if block.is_noise:
                continue

            if block.page != current_page:
                if current_page is not None:
                    self._flush_page_figures(lines, meta_anchors, figure_refs_by_page, current_page)
                    lines.append("")
                lines.extend(self.markdown_renderer.render_page_marker(block.page))
                current_page = block.page

            if block.type == "table":
                table_ref = table_refs.get(block.block_id)
                if table_ref is not None:
                    lines.extend(self.markdown_renderer.render_table_ref(table_ref, block))
                    meta_anchors.append(
                        {
                            "anchor_id": table_ref["anchor_id"],
                            "type": "table",
                            "page_no": table_ref["page_no"],
                            "table_id": table_ref["table_id"],
                            "caption": table_ref["caption"],
                            "table_path": table_ref["table_path"],
                            "screenshot_path": table_ref["screenshot_path"],
                        }
                    )
                continue

            if block.type == "caption" and self._looks_like_figure_caption(block.text):
                figure_ref = self._pop_figure_ref_for_caption(figure_caption_map, figure_refs_by_page, block)
                if figure_ref is not None:
                    lines.extend(self.markdown_renderer.render_figure_ref(figure_ref))
                    meta_anchors.append(
                        {
                            "anchor_id": figure_ref["anchor_id"],
                            "type": "figure",
                            "page_no": figure_ref["page_no"],
                            "figure_id": figure_ref["figure_id"],
                            "caption": figure_ref["caption"],
                            "image_path": figure_ref["image_path"],
                        }
                    )
                    continue

            anchor_entry = self._build_text_anchor_entry(block, section_maps, text_counters)
            lines.extend(self.markdown_renderer.render_text_anchor(anchor_entry["anchor_id"]))
            lines.extend(self.markdown_renderer.render_text_block(block))
            meta_anchors.append(anchor_entry)

        if current_page is not None:
            self._flush_page_figures(lines, meta_anchors, figure_refs_by_page, current_page)

        markdown = "\n".join(lines).strip() + "\n"
        paper_meta = {
            "doc_id": document.doc_id,
            "source_pdf": document.source_file,
            "total_pages": len(document.pages),
            "parser_version": self.PARSER_VERSION,
            "anchors": meta_anchors,
        }
        return markdown, paper_meta

    def _build_text_anchor_entry(
        self,
        block: PaperBlock,
        section_maps: dict[str, dict[str, str | int]],
        text_counters: defaultdict[tuple[int, int], int],
    ) -> dict:
        section_no = int(section_maps["section_no_by_block"].get(block.block_id, 0))
        section_title = str(section_maps["section_title_by_block"].get(block.block_id, "Front Matter"))
        counter_key = (block.page, section_no)
        text_counters[counter_key] += 1
        anchor_id = f"P{block.page}_S{section_no}_Para_{text_counters[counter_key]:02d}"

        return {
            "anchor_id": anchor_id,
            "type": block.type,
            "page_no": block.page,
            "section": section_title,
            "text": self.markdown_renderer.clean_text(block.text),
        }

    def _build_section_maps(self, section_tree: list[SectionNode]) -> dict[str, dict[str, str | int]]:
        section_no_by_block: dict[str, int] = {}
        section_title_by_block: dict[str, str] = {}

        ordinal = 0
        for node in section_tree:
            if node.section_id != "front_matter":
                ordinal += 1
            section_no = ordinal
            section_title = node.title
            for block_id in node.block_ids:
                section_no_by_block[block_id] = section_no
                section_title_by_block[block_id] = section_title

        return {
            "section_no_by_block": section_no_by_block,
            "section_title_by_block": section_title_by_block,
        }

    def _build_figure_caption_queues(self, clean_blocks: list[PaperBlock]) -> dict[int, deque[str]]:
        caption_queues: dict[int, deque[str]] = defaultdict(deque)
        for block in clean_blocks:
            if block.is_noise or block.type != "caption":
                continue
            if self._looks_like_figure_caption(block.text):
                caption_queues[block.page].append(self.markdown_renderer.clean_text(block.text))
        return caption_queues

    @staticmethod
    def _group_by_page(items: list[dict[str, str | int]]) -> dict[int, deque[dict[str, str | int]]]:
        grouped: dict[int, deque[dict[str, str | int]]] = defaultdict(deque)
        for item in items:
            grouped[int(item["page_no"])].append(item)
        return grouped

    @staticmethod
    def _group_figure_ref_by_caption(
        figure_refs: list[dict[str, str | int]],
    ) -> dict[tuple[int, str], deque[dict[str, str | int]]]:
        mapping: dict[tuple[int, str], deque[dict[str, str | int]]] = defaultdict(deque)
        for ref in figure_refs:
            key = (int(ref["page_no"]), str(ref["caption"]).strip().lower())
            mapping[key].append(ref)
        return mapping

    def _pop_figure_ref_for_caption(
        self,
        figure_caption_map: dict[tuple[int, str], deque[dict[str, str | int]]],
        figure_refs_by_page: dict[int, deque[dict[str, str | int]]],
        block: PaperBlock,
    ) -> dict[str, str | int] | None:
        key = (block.page, self.markdown_renderer.clean_text(block.text).strip().lower())
        queue = figure_caption_map.get(key)
        if queue:
            ref = queue.popleft()
            page_queue = figure_refs_by_page.get(block.page, deque())
            try:
                page_queue.remove(ref)
            except ValueError:
                pass
            return ref

        page_queue = figure_refs_by_page.get(block.page)
        if page_queue:
            return page_queue.popleft()
        return None

    def _flush_page_figures(
        self,
        lines: list[str],
        meta_anchors: list[dict],
        figure_refs_by_page: dict[int, deque[dict[str, str | int]]],
        page_no: int,
    ) -> None:
        page_queue = figure_refs_by_page.get(page_no)
        if not page_queue:
            return

        while page_queue:
            figure_ref = page_queue.popleft()
            lines.extend(self.markdown_renderer.render_figure_ref(figure_ref))
            meta_anchors.append(
                {
                    "anchor_id": figure_ref["anchor_id"],
                    "type": "figure",
                    "page_no": figure_ref["page_no"],
                    "figure_id": figure_ref["figure_id"],
                    "caption": figure_ref["caption"],
                    "image_path": figure_ref["image_path"],
                }
            )

    @staticmethod
    def _looks_like_figure_caption(text: str) -> bool:
        compact = re.sub(r"\s+", " ", text).strip().lower()
        return compact.startswith("figure ") or compact.startswith("fig.")
