from __future__ import annotations

import asyncio
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .env_loader import load_parser_service_env
from .converter import DoclingLaptopConverter, DoclingNotInstalledError
from .llm_converter import OpenAICompatibleConfigError, OpenAICompatiblePdfConverter

load_parser_service_env()

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
RUNS_ROOT = PROJECT_ROOT / "outputs" / "api_runs"

HOST = os.getenv("DOCLING_PARSER_HOST", "127.0.0.1").strip() or "127.0.0.1"
PORT = int(os.getenv("DOCLING_PARSER_PORT", "8010") or "8010")
CONVERSION_SEMAPHORE = asyncio.Semaphore(1)
PARSE_PROGRESS: dict[str, dict[str, object]] = {}
PARSE_PROGRESS_LOCK = Lock()

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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_fraction(value: object) -> float | None:
    try:
        fraction = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, fraction))


def _set_parse_progress(
    submission_id: str,
    *,
    provider: str | None = None,
    status: str | None = None,
    phase: str | None = None,
    message: str | None = None,
    fraction: object = None,
    current_chunk: int | None = None,
    total_chunks: int | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
) -> dict[str, object]:
    with PARSE_PROGRESS_LOCK:
        payload = dict(PARSE_PROGRESS.get(submission_id, {}))
        payload["submissionId"] = submission_id
        payload["updatedAt"] = _utc_now_iso()

        if provider is not None:
            payload["provider"] = provider
        if status is not None:
            payload["status"] = status
        if phase is not None:
            payload["phase"] = phase
        if message is not None:
            payload["message"] = message

        normalized_fraction = _normalize_fraction(fraction)
        if normalized_fraction is not None:
            payload["fraction"] = normalized_fraction
            payload["percent"] = round(normalized_fraction * 100, 1)

        optional_fields = {
            "currentChunk": current_chunk,
            "totalChunks": total_chunks,
            "pageStart": page_start,
            "pageEnd": page_end,
        }
        for key, value in optional_fields.items():
            if value is None:
                payload.pop(key, None)
            else:
                payload[key] = value

        PARSE_PROGRESS[submission_id] = payload
        return dict(payload)


def _get_parse_progress(submission_id: str) -> dict[str, object] | None:
    with PARSE_PROGRESS_LOCK:
        payload = PARSE_PROGRESS.get(submission_id)
    return dict(payload) if payload else None


def _normalize_provider(value: object) -> str:
    provider = str(value or "docling").strip().lower()
    return provider if provider in {"docling", "llm"} else "docling"


def _provider_display_name(provider: str) -> str:
    return "LLM PDF" if provider == "llm" else "Docling"


def _build_converter(provider: str):
    if provider == "llm":
        return OpenAICompatiblePdfConverter()
    return DoclingLaptopConverter()


@app.get("/health")
def health() -> dict[str, object]:
    providers: dict[str, dict[str, object]] = {}

    try:
        converter = DoclingLaptopConverter()
        providers["docling"] = {
            "available": True,
            "profile": converter.profile,
        }
    except DoclingNotInstalledError as exc:
        providers["docling"] = {
            "available": False,
            "message": str(exc),
        }

    try:
        converter = OpenAICompatiblePdfConverter()
        providers["llm"] = {
            "available": True,
            "profile": converter.profile,
        }
    except OpenAICompatibleConfigError as exc:
        providers["llm"] = {
            "available": False,
            "message": str(exc),
        }

    all_available = all(bool(item.get("available")) for item in providers.values())
    return {
        "status": "ok" if all_available else "degraded",
        "engine": "docling_parser_service",
        "providers": providers,
    }


@app.get("/papers/parse-progress/{submission_id}")
def get_parse_progress(submission_id: str) -> dict[str, object]:
    payload = _get_parse_progress(submission_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Parse progress not found.")
    return payload


@app.post("/papers/parse")
async def parse_paper(
    request: Request,
    paper: UploadFile = File(...),
    submission_id: str | None = Form(None),
    provider: str | None = Form(None),
) -> dict:
    original_name = Path(paper.filename or "paper.pdf").name
    suffix = Path(original_name).suffix or ".pdf"
    normalized_provider = _normalize_provider(provider)
    provider_name = _provider_display_name(normalized_provider)

    if suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    submission_id = (submission_id or "").strip() or uuid4().hex
    _set_parse_progress(
        submission_id,
        provider=normalized_provider,
        status="queued",
        phase="queued",
        message=f"queued '{original_name}' for {provider_name} parsing",
        fraction=0.0,
    )
    upload_root = _ensure_directory(RUNS_ROOT / submission_id / "input")
    output_root = _ensure_directory(RUNS_ROOT / submission_id)
    uploaded_pdf_path = upload_root / original_name

    with uploaded_pdf_path.open("wb") as buffer:
        shutil.copyfileobj(paper.file, buffer)

    _set_parse_progress(
        submission_id,
        provider=normalized_provider,
        status="processing",
        phase="preparing",
        message=f"uploaded '{original_name}', preparing {provider_name} parser",
        fraction=0.08,
    )

    try:
        converter = _build_converter(normalized_provider)
    except (DoclingNotInstalledError, OpenAICompatibleConfigError) as exc:
        _set_parse_progress(
            submission_id,
            provider=normalized_provider,
            status="failed",
            phase="failed",
            message=str(exc),
            fraction=0.08,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    def handle_progress(payload: dict[str, object]) -> None:
        _set_parse_progress(
            submission_id,
            provider=normalized_provider,
            status="processing",
            phase=str(payload.get("phase") or "parsing"),
            message=str(payload.get("message") or ""),
            fraction=payload.get("fraction"),
            current_chunk=payload.get("current_chunk"),
            total_chunks=payload.get("total_chunks"),
            page_start=payload.get("page_start"),
            page_end=payload.get("page_end"),
        )

    try:
        async with CONVERSION_SEMAPHORE:
            result = await run_in_threadpool(
                converter.convert_pdf,
                uploaded_pdf_path,
                output_root,
                handle_progress,
            )
    except Exception as exc:
        _set_parse_progress(
            submission_id,
            provider=normalized_provider,
            status="failed",
            phase="failed",
            message=f"{provider_name} conversion failed: {exc}",
            fraction=1.0,
        )
        raise HTTPException(status_code=500, detail=f"{provider_name} conversion failed: {exc}") from exc

    markdown_path = Path(result["markdown_path"])
    paper_meta_path = Path(result["paper_meta_path"])
    bundle_dir = Path(result["bundle_dir"])

    _set_parse_progress(
        submission_id,
        provider=normalized_provider,
        status="completed",
        phase="completed",
        message=f"parsed '{original_name}' successfully",
        fraction=1.0,
    )

    return {
        "submissionId": submission_id,
        "paperName": original_name,
        "paperMarkdown": markdown_path.read_text(encoding="utf-8"),
        "paperAssetBase": _build_asset_base(request, submission_id),
        "paperMeta": _read_json(paper_meta_path),
        "provider": normalized_provider,
        "artifacts": {
            "markdownPath": str(markdown_path),
            "paperMetaPath": str(paper_meta_path),
            "bundleDir": str(bundle_dir),
            "outputDir": str(output_root),
            "doclingDocumentPath": str(result.get("docling_document_path", "")),
            "llmResultPath": str(result.get("llm_result_path", "")),
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
