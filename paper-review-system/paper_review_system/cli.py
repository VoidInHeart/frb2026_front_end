from __future__ import annotations

import argparse
from pathlib import Path

from .api.review_pipeline import ReviewPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paper review system CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert_parser = subparsers.add_parser("convert", help="Convert PDF to Markdown and IR")
    convert_parser.add_argument("pdf", type=Path, help="Path to input PDF")
    convert_parser.add_argument("--output-dir", type=Path, default=Path("outputs"))

    review_parser = subparsers.add_parser("review", help="Generate full review report")
    review_parser.add_argument("pdf", type=Path, help="Path to input PDF")
    review_parser.add_argument("--output-dir", type=Path, default=Path("outputs"))

    return parser


def main() -> None:
    args = build_parser().parse_args()
    pipeline = ReviewPipeline()

    if args.command == "convert":
        result = pipeline.convert_pdf(args.pdf, args.output_dir)
        print(f"Markdown written to: {result['markdown_path']}")
        print(f"Document IR written to: {result['document_ir_path']}")
        print(f"Evidence IR written to: {result['evidence_ir_path']}")
        return

    if args.command == "review":
        result = pipeline.review_pdf(args.pdf, args.output_dir)
        print(f"Markdown written to: {result['markdown_path']}")
        print(f"Review report written to: {result['review_report_path']}")


if __name__ == "__main__":
    main()
