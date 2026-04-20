from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .converter import DoclingLaptopConverter, DoclingNotInstalledError

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
RUNS_ROOT = PROJECT_ROOT / "outputs" / "api_runs"

HOST = os.getenv("DOCLING_PARSER_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.getenv("DOCLING_PARSER_PORT", "8010") or "8010")
CONVERSION_SEMAPHORE = asyncio.Semaphore(1)

app = FastAPI(title="Docling Parser Service", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/assets", StaticFiles(directory=str(RUNS_ROOT), check_dir=False), name="assets")


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_asset_base(request: Request, submission_id: str) -> str:
    return f"{str(request.base_url).rstrip('/')}/assets/{submission_id}/paper_bundle"


@app.get("/health")
def health() -> dict[str, object]:
    try:
        converter = DoclingLaptopConverter()
        return {
            "status": "ok",
            "engine": "docling",
            "docling_available": True,
            "profile": converter.profile,
        }
    except DoclingNotInstalledError as exc:
        return {
            "status": "degraded",
            "engine": "docling",
            "docling_available": False,
            "message": str(exc),
        }


@app.post("/papers/parse")
async def parse_paper(
    request: Request,
    paper: UploadFile = File(...),
) -> dict:
    original_name = Path(paper.filename or "paper.pdf").name
    suffix = Path(original_name).suffix or ".pdf"

    if suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    submission_id = uuid4().hex
    upload_root = _ensure_directory(RUNS_ROOT / submission_id / "input")
    output_root = _ensure_directory(RUNS_ROOT / submission_id)
    uploaded_pdf_path = upload_root / original_name

    with uploaded_pdf_path.open("wb") as buffer:
        shutil.copyfileobj(paper.file, buffer)

    try:
        converter = DoclingLaptopConverter()
    except DoclingNotInstalledError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        async with CONVERSION_SEMAPHORE:
            result = await run_in_threadpool(converter.convert_pdf, uploaded_pdf_path, output_root)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Docling conversion failed: {exc}") from exc

    markdown_path = Path(result["markdown_path"])
    paper_meta_path = Path(result["paper_meta_path"])
    bundle_dir = Path(result["bundle_dir"])

    return {
        "submissionId": submission_id,
        "paperName": original_name,
        "paperMarkdown": markdown_path.read_text(encoding="utf-8"),
        "paperAssetBase": _build_asset_base(request, submission_id),
        "paperMeta": _read_json(paper_meta_path),
        "artifacts": {
            "markdownPath": str(markdown_path),
            "paperMetaPath": str(paper_meta_path),
            "bundleDir": str(bundle_dir),
            "outputDir": str(output_root),
            "doclingDocumentPath": str(result["docling_document_path"]),
        },
    }


def main() -> None:
    uvicorn.run(
        "docling_parser_service.app:app",
        host=HOST,
        port=PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
