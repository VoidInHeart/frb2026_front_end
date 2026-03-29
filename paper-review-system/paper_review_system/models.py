from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value


@dataclass(slots=True)
class PageInfo:
    page: int
    width: float
    height: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PaperBlock:
    block_id: str
    page: int
    bbox: list[float]
    type: str
    text: str
    level: int | None = None
    is_noise: bool = False
    font_size: float | None = None
    source: str = "pdf"
    role: str | None = None
    table_headers: list[str] | None = None
    table_rows: list[list[str]] | None = None
    table_caption: str | None = None
    table_caption_position: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(asdict(self))


@dataclass(slots=True)
class SectionNode:
    section_id: str
    title: str
    level: int
    page_start: int
    page_end: int
    block_ids: list[str] = field(default_factory=list)
    parent_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(asdict(self))


@dataclass(slots=True)
class PaperAnchor:
    anchor_id: str
    block_id: str
    page: int
    bbox: list[float]
    text: str
    section_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(asdict(self))


@dataclass(slots=True)
class PaperDocument:
    doc_id: str
    source_file: str
    pages: list[PageInfo]
    blocks: list[PaperBlock]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source_file": self.source_file,
            "pages": [page.to_dict() for page in self.pages],
            "blocks": [block.to_dict() for block in self.blocks],
            "metadata": _drop_none(self.metadata),
        }


@dataclass(slots=True)
class EvidenceBundle:
    doc_id: str
    anchors: list[PaperAnchor]
    clean_blocks: list[PaperBlock]
    raw_blocks: list[PaperBlock]
    section_tree: list[SectionNode]

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "anchors": [anchor.to_dict() for anchor in self.anchors],
            "clean_blocks": [block.to_dict() for block in self.clean_blocks],
            "raw_blocks": [block.to_dict() for block in self.raw_blocks],
            "section_tree": [node.to_dict() for node in self.section_tree],
        }


def build_doc_id(source_file: str) -> str:
    stem = Path(source_file).stem
    safe_stem = "".join(ch if ch.isalnum() else "_" for ch in stem).strip("_") or "paper"
    return safe_stem.lower()
