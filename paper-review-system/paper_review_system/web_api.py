from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from paper_review_system.api.review_pipeline import ReviewPipeline
from paper_review_system.io_utils import ensure_directory

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
RUNS_ROOT = PROJECT_ROOT / "outputs" / "api_runs"

app = FastAPI(title="Paper Review System API", version="0.1.0")
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


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_asset_base(request: Request, submission_id: str) -> str:
    return f"{str(request.base_url).rstrip('/')}/assets/{submission_id}"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    upload_root = ensure_directory(RUNS_ROOT / submission_id / "input")
    output_root = ensure_directory(RUNS_ROOT / submission_id)
    uploaded_pdf_path = upload_root / original_name

    with uploaded_pdf_path.open("wb") as buffer:
        shutil.copyfileobj(paper.file, buffer)

    pipeline = ReviewPipeline()
    result = pipeline.convert_pdf(uploaded_pdf_path, output_root)

    markdown_path = Path(result["markdown_path"])
    paper_meta_path = Path(result["paper_meta_path"])
    bundle_dir = Path(result["bundle_dir"])

    return {
        "submissionId": submission_id,
        "paperName": original_name,
        "paperMarkdown": markdown_path.read_text(encoding="utf-8"),
        "paperAssetBase": f"{_build_asset_base(request, submission_id)}/paper_bundle",
        "paperMeta": _read_json(paper_meta_path),
        "artifacts": {
            "markdownPath": str(markdown_path),
            "paperMetaPath": str(paper_meta_path),
            "bundleDir": str(bundle_dir),
            "outputDir": str(output_root),
        },
    }


def main() -> None:
    uvicorn.run(
        "paper_review_system.web_api:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
