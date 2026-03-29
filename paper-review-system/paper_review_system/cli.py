from __future__ import annotations

import argparse
from pathlib import Path

from .api.review_pipeline import ReviewPipeline
from .web_api import main as serve_api


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paper parser CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert_parser = subparsers.add_parser("convert", help="Convert PDF to Markdown and IR")
    convert_parser.add_argument("pdf", type=Path, help="Path to input PDF")
    convert_parser.add_argument("--output-dir", type=Path, default=Path("outputs"))

    subparsers.add_parser("serve", help="Start the local parse API")

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "serve":
        serve_api()
        return

    pipeline = ReviewPipeline()
    result = pipeline.convert_pdf(args.pdf, args.output_dir)
    print(f"Markdown written to: {result['markdown_path']}")
    print(f"Document IR written to: {result['document_ir_path']}")
    print(f"Evidence IR written to: {result['evidence_ir_path']}")


if __name__ == "__main__":
    main()
