from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict
from urllib import error, request
from urllib.parse import urlparse
from uuid import uuid4

from .converter import (
    _build_origin_metadata,
    _collect_reference_diagnostics,
    _count_pdf_pages,
    _ensure_directory,
    _log_progress,
    _parse_markdown_blocks,
    _postprocess_markdown,
)
from .env_loader import load_parser_service_env


class OpenAICompatibleConfigError(RuntimeError):
    pass


def _normalize_title_key(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip().lower()


def _coerce_page_no(value: Any) -> int | None:
    try:
        page_no = int(value)
    except (TypeError, ValueError):
        return None
    return page_no if page_no > 0 else None


def _coerce_response_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return str(content or "").strip()

    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            if item.strip():
                parts.append(item.strip())
            continue
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", "") or "").strip().lower()
        if item_type in {"text", "output_text"}:
            text = str(item.get("text", "") or "").strip()
            if text:
                parts.append(text)
            continue
        if item_type == "refusal":
            refusal = str(item.get("refusal", "") or "").strip()
            if refusal:
                parts.append(refusal)
    return "\n".join(parts).strip()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None

    candidates = [raw]
    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, flags=re.DOTALL)
    if fenced_match:
        candidates.append(fenced_match.group(1).strip())

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidates.append(raw[start : end + 1].strip())

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    return None


def _normalize_markdown_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    fenced = re.fullmatch(r"```(?:markdown|md)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return text


def _is_dashscope_compatible_base_url(base_url: str) -> bool:
    host = urlparse(str(base_url or "").strip()).netloc.lower()
    return "dashscope.aliyuncs.com" in host


def _normalize_section_hints(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    out: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        title = str(
            item.get("section_title")
            or item.get("title")
            or item.get("heading")
            or item.get("name")
            or ""
        ).strip()
        if not title:
            continue
        out.append(
            {
                "order": index,
                "section_title": title,
                "page_no": _coerce_page_no(item.get("page_no") or item.get("page")),
                "summary": str(item.get("summary", "") or "").strip(),
            }
        )
    return out


def _normalize_visual_items(items: Any, *, kind: str) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    out: list[dict[str, Any]] = []
    label_prefix = "Figure" if kind == "figure" else "Table"
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue

        label = str(item.get("label") or item.get("name") or "").strip()
        caption = str(item.get("caption", "") or "").strip()
        description = str(item.get("description") or item.get("summary") or "").strip()
        markdown = _normalize_markdown_text(item.get("markdown") or item.get("table_markdown"))
        page_no = _coerce_page_no(item.get("page_no") or item.get("page"))
        section_title = str(item.get("section_title") or item.get("section") or "").strip()

        out.append(
            {
                "id": str(item.get(f"{kind}_id") or item.get("id") or f"{kind}_{index:03d}"),
                "label": label or f"{label_prefix} {index}",
                "caption": caption,
                "description": description,
                "markdown": markdown,
                "page_no": page_no,
                "section_title": section_title,
            }
        )
    return out


def _extract_sections_from_markdown(markdown: str, section_hints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    leading_lines, blocks = _parse_markdown_blocks(markdown)
    hint_map = {_normalize_title_key(item.get("section_title", "")): item for item in section_hints}
    sections: list[dict[str, Any]] = []

    preface = "\n".join(line for line in leading_lines if str(line).strip()).strip()
    if preface:
        sections.append(
            {
                "section_title": "document",
                "content": preface,
                "level": 1,
                "page_no": None,
            }
        )

    for block in blocks:
        title = str(block.get("title", "") or "").strip()
        if not title:
            continue
        hint = hint_map.get(_normalize_title_key(title), {})
        body_lines = [str(line) for line in block.get("body", [])]
        content = "\n".join(body_lines).strip()
        sections.append(
            {
                "section_title": title,
                "content": content,
                "level": int(block.get("level", 2) or 2),
                "page_no": _coerce_page_no(hint.get("page_no")),
            }
        )

    return sections


def _build_anchor_records(
    sections: list[dict[str, Any]],
    figures: list[dict[str, Any]],
    tables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []

    for index, section in enumerate(sections, start=1):
        title = str(section.get("section_title", "") or "").strip()
        content = str(section.get("content", "") or "").strip()
        if not content:
            continue
        anchors.append(
            {
                "anchor_id": f"paragraph_{index:03d}",
                "type": "paragraph",
                "page_no": _coerce_page_no(section.get("page_no")) or 1,
                "section": title,
                "text": content[:400],
            }
        )

    for index, item in enumerate(figures, start=1):
        anchors.append(
            {
                "anchor_id": f"figure_{index:03d}",
                "type": "figure",
                "page_no": _coerce_page_no(item.get("page_no")) or 1,
                "section": str(item.get("section_title", "") or "").strip(),
                "caption": str(item.get("caption", "") or "").strip()
                or str(item.get("label", "") or "").strip(),
                "text": str(item.get("description", "") or "").strip(),
                "figure_id": str(item.get("id", "") or f"figure_{index:03d}"),
            }
        )

    for index, item in enumerate(tables, start=1):
        anchors.append(
            {
                "anchor_id": f"table_{index:03d}",
                "type": "table",
                "page_no": _coerce_page_no(item.get("page_no")) or 1,
                "section": str(item.get("section_title", "") or "").strip(),
                "caption": str(item.get("caption", "") or "").strip()
                or str(item.get("label", "") or "").strip(),
                "text": (str(item.get("markdown", "") or "") or str(item.get("description", "") or "")).strip()[:700],
                "table_id": str(item.get("id", "") or f"table_{index:03d}"),
            }
        )

    return anchors


def _build_prompt(pdf_name: str) -> str:
    return (
        "Parse the attached PDF academic paper and return only one JSON object. "
        "Preserve the paper language. "
        "The JSON schema is: "
        '{"title":"string","abstract":"string","paper_markdown":"string",'
        '"sections":[{"section_title":"string","page_no":1}],'
        '"figures":[{"id":"string","label":"Figure 1","caption":"string","page_no":1,"description":"string","section_title":"string"}],'
        '"tables":[{"id":"string","label":"Table 1","caption":"string","page_no":1,"section_title":"string","markdown":"|col|col|"}]}. '
        "Rules: "
        "1) paper_markdown must be complete academic markdown with ATX headings. "
        "2) Convert tables to markdown tables whenever legible. "
        "3) Keep references in markdown. "
        "4) For figures, keep the original caption and add a short textual description in nearby markdown using blockquote lines, but do not invent image URLs. "
        "5) Do not wrap the JSON in code fences. "
        f"6) Source filename: {pdf_name}."
    )


class OpenAICompatiblePdfConverter:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_file_mb: int | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        request_callable: Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]] | None = None,
        file_upload_callable: Callable[[str, dict[str, str], Path, float], dict[str, Any]] | None = None,
        file_retrieve_callable: Callable[[str, dict[str, str], float], dict[str, Any]] | None = None,
    ) -> None:
        load_parser_service_env()
        self.api_key = str(api_key or os.getenv("OPENAI_PDF_PARSER_API_KEY", "")).strip()
        self.base_url = str(base_url or os.getenv("OPENAI_PDF_PARSER_BASE_URL", "https://api.openai.com/v1")).strip()
        self.model = str(model or os.getenv("OPENAI_PDF_PARSER_MODEL", "gpt-4.1")).strip()
        self.timeout_seconds = float(timeout_seconds or os.getenv("OPENAI_PDF_PARSER_TIMEOUT_SECONDS", "180") or "180")
        self.max_file_mb = int(max_file_mb or os.getenv("OPENAI_PDF_PARSER_MAX_FILE_MB", "20") or "20")
        self.max_tokens = int(max_tokens or os.getenv("OPENAI_PDF_PARSER_MAX_TOKENS", "16000") or "16000")
        self.temperature = float(temperature or os.getenv("OPENAI_PDF_PARSER_TEMPERATURE", "0") or "0")
        self._request_callable = request_callable or self._default_request
        self._file_upload_callable = file_upload_callable or self._default_file_upload_request
        self._file_retrieve_callable = file_retrieve_callable or self._default_get_request

        if not self.api_key:
            raise OpenAICompatibleConfigError(
                "OPENAI_PDF_PARSER_API_KEY is required for provider=llm."
            )
        if not self.base_url:
            raise OpenAICompatibleConfigError(
                "OPENAI_PDF_PARSER_BASE_URL is required for provider=llm."
            )
        if not self.model:
            raise OpenAICompatibleConfigError(
                "OPENAI_PDF_PARSER_MODEL is required for provider=llm."
            )
        if _is_dashscope_compatible_base_url(self.base_url) and self.model not in {"qwen-long", "qwen-doc-turbo"}:
            raise OpenAICompatibleConfigError(
                "DashScope PDF parsing currently requires OPENAI_PDF_PARSER_MODEL to be `qwen-long` or `qwen-doc-turbo`."
            )

        self.profile = {
            "base_url": self.base_url,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_file_mb": self.max_file_mb,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "provider_family": "dashscope" if _is_dashscope_compatible_base_url(self.base_url) else "generic_openai_compatible",
        }
        self._dashscope_file_ready_retries = max(
            1,
            int(os.getenv("OPENAI_PDF_PARSER_FILE_READY_RETRIES", "10") or "10"),
        )
        self._dashscope_file_ready_poll_seconds = max(
            1.0,
            float(os.getenv("OPENAI_PDF_PARSER_FILE_READY_POLL_SECONDS", "2") or "2"),
        )

    def convert_pdf(
        self,
        pdf_path: str | Path,
        output_dir: str | Path,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> Dict[str, str]:
        def emit_progress(message: str, *, phase: str, fraction: float, **extra: Any) -> None:
            normalized_fraction = max(0.0, min(1.0, float(fraction)))
            _log_progress(message)
            if progress_callback:
                progress_callback(
                    {
                        "phase": phase,
                        "fraction": normalized_fraction,
                        "message": message,
                        **extra,
                    }
                )

        pdf_path = Path(pdf_path).resolve()
        output_root = _ensure_directory(Path(output_dir).resolve())
        bundle_root = _ensure_directory(output_root / "paper_bundle")
        assets_root = _ensure_directory(bundle_root / "assets")
        markdown_path = bundle_root / "paper.md"
        paper_meta_path = bundle_root / "paper_meta.json"
        raw_result_path = bundle_root / "llm_parse_result.json"

        total_pages = _count_pdf_pages(pdf_path)
        file_size = pdf_path.stat().st_size
        if file_size > self.max_file_mb * 1024 * 1024:
            raise RuntimeError(
                f"PDF is too large for LLM parsing: {file_size / (1024 * 1024):.1f} MB > {self.max_file_mb} MB."
            )

        emit_progress(
            f"starting llm parsing for '{pdf_path.name}' ({total_pages} pages)",
            phase="preparing",
            fraction=0.05,
            current_chunk=1,
            total_chunks=1,
            page_start=1,
            page_end=total_pages,
        )
        emit_progress(
            f"uploading '{pdf_path.name}' to llm parser",
            phase="uploading",
            fraction=0.18,
            current_chunk=1,
            total_chunks=1,
            page_start=1,
            page_end=total_pages,
        )
        if _is_dashscope_compatible_base_url(self.base_url):
            emit_progress(
                f"uploaded '{pdf_path.name}', waiting for DashScope file parsing",
                phase="preparing",
                fraction=0.34,
                current_chunk=1,
                total_chunks=1,
                page_start=1,
                page_end=total_pages,
            )
            response_data = self._invoke_dashscope_document_chat(pdf_path)
        else:
            payload = self._build_chat_completions_payload(pdf_path)
            response_data = self._invoke_chat_completions(payload)

        emit_progress(
            "received llm parser response, normalizing markdown",
            phase="parsing",
            fraction=0.72,
            current_chunk=1,
            total_chunks=1,
            page_start=1,
            page_end=total_pages,
        )

        normalized = self._normalize_parse_result(response_data, pdf_path=pdf_path)
        markdown = _postprocess_markdown(normalized["paper_markdown"])
        _ensure_directory(markdown_path.parent)
        markdown_path.write_text(markdown, encoding="utf-8")
        _ensure_directory(raw_result_path.parent)
        raw_result_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")

        reference_diagnostics = _collect_reference_diagnostics(markdown)
        paper_meta = self._build_paper_meta(
            pdf_path=pdf_path,
            llm_result_path=raw_result_path,
            assets_root=assets_root,
            total_pages=total_pages,
            normalized=normalized,
            markdown=markdown,
            reference_diagnostics=reference_diagnostics,
        )
        _ensure_directory(paper_meta_path.parent)
        paper_meta_path.write_text(json.dumps(paper_meta, ensure_ascii=False, indent=2), encoding="utf-8")

        emit_progress(
            f"wrote llm paper bundle to '{bundle_root}'",
            phase="writing",
            fraction=0.96,
            current_chunk=1,
            total_chunks=1,
            page_start=1,
            page_end=total_pages,
        )

        return {
            "bundle_dir": str(bundle_root.resolve()),
            "markdown_path": str(markdown_path.resolve()),
            "paper_meta_path": str(paper_meta_path.resolve()),
            "llm_result_path": str(raw_result_path.resolve()),
        }

    def _build_chat_completions_payload(self, pdf_path: Path) -> dict[str, Any]:
        file_b64 = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
        file_data = f"data:application/pdf;base64,{file_b64}"
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You are a careful scientific PDF parser.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": _build_prompt(pdf_path.name),
                        },
                        {
                            "type": "file",
                            "file": {
                                "filename": pdf_path.name,
                                "file_data": file_data,
                            },
                        },
                    ],
                },
            ],
        }

    def _build_dashscope_chat_payload(self, *, file_id: str, pdf_path: Path) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You are a careful scientific PDF parser.",
                },
                {
                    "role": "system",
                    "content": f"fileid://{file_id}",
                },
                {
                    "role": "user",
                    "content": _build_prompt(pdf_path.name),
                },
            ],
        }

    def _invoke_chat_completions(self, body: dict[str, Any]) -> dict[str, Any]:
        endpoint = self.base_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            return self._request_callable(endpoint, headers, body, self.timeout_seconds)
        except RuntimeError:
            body_without_json_mode = dict(body)
            body_without_json_mode.pop("response_format", None)
            return self._request_callable(endpoint, headers, body_without_json_mode, self.timeout_seconds)

    def _invoke_dashscope_document_chat(self, pdf_path: Path) -> dict[str, Any]:
        file_id = self._upload_file_for_dashscope(pdf_path)
        self._wait_for_dashscope_file_ready(file_id)
        body = self._build_dashscope_chat_payload(file_id=file_id, pdf_path=pdf_path)
        return self._invoke_dashscope_chat_with_retry(body)

    def _upload_file_for_dashscope(self, pdf_path: Path) -> str:
        endpoint = self.base_url.rstrip("/")
        if not endpoint.endswith("/files"):
            endpoint = f"{endpoint}/files"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        response_data = self._file_upload_callable(endpoint, headers, pdf_path, self.timeout_seconds)
        if not isinstance(response_data, dict):
            raise RuntimeError("DashScope file upload returned a non-object payload.")

        data_obj = response_data.get("data", {}) if isinstance(response_data.get("data"), dict) else {}
        file_id = str(response_data.get("id") or response_data.get("file_id") or data_obj.get("id") or "").strip()
        if not file_id:
            raise RuntimeError(f"DashScope file upload did not return a file id: {response_data}")
        return file_id

    def _wait_for_dashscope_file_ready(self, file_id: str) -> None:
        endpoint = self.base_url.rstrip("/")
        if not endpoint.endswith("/files"):
            endpoint = f"{endpoint}/files"
        endpoint = f"{endpoint}/{file_id}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        last_payload: dict[str, Any] | None = None

        for attempt in range(self._dashscope_file_ready_retries):
            payload = self._file_retrieve_callable(endpoint, headers, self.timeout_seconds)
            if not isinstance(payload, dict):
                break
            last_payload = payload
            if self._is_dashscope_file_ready(payload):
                return
            time.sleep(self._dashscope_file_ready_poll_seconds)

        if last_payload is not None:
            raise RuntimeError(
                "DashScope file parsing did not finish in time. "
                f"Last file status payload: {last_payload}"
            )

    def _is_dashscope_file_ready(self, payload: dict[str, Any]) -> bool:
        status_candidates = [
            payload.get("status"),
            payload.get("state"),
        ]
        data = payload.get("data", {})
        if isinstance(data, dict):
            status_candidates.extend([data.get("status"), data.get("state")])

        normalized = [str(item or "").strip().lower() for item in status_candidates if str(item or "").strip()]
        if not normalized:
            return True
        if any(item in {"processed", "done", "success", "succeeded", "ready", "completed"} for item in normalized):
            return True
        if any(item in {"failed", "error"} for item in normalized):
            raise RuntimeError(f"DashScope file parsing failed: {payload}")
        return False

    def _invoke_dashscope_chat_with_retry(self, body: dict[str, Any]) -> dict[str, Any]:
        last_exc: RuntimeError | None = None
        for attempt in range(self._dashscope_file_ready_retries):
            try:
                return self._invoke_chat_completions(body)
            except RuntimeError as exc:
                message = str(exc)
                last_exc = exc
                lowered = message.lower()
                if "file parsing in progress" not in lowered and "processing" not in lowered:
                    raise
                time.sleep(self._dashscope_file_ready_poll_seconds)
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("DashScope chat invocation failed with unknown error.")

    def _default_request(
        self,
        endpoint: str,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = request.Request(endpoint, data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LLM parser request failed: HTTP {exc.code} {body_text[:600]}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"LLM parser request failed: {exc.reason}") from exc

    def _default_file_upload_request(
        self,
        endpoint: str,
        headers: dict[str, str],
        pdf_path: Path,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        boundary = f"----CodexPdfBoundary{uuid4().hex}"
        newline = b"\r\n"
        file_bytes = pdf_path.read_bytes()

        parts = [
            f"--{boundary}".encode("utf-8"),
            b'Content-Disposition: form-data; name="purpose"',
            b"",
            b"file-extract",
            f"--{boundary}".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="file"; filename="{pdf_path.name}"'
            ).encode("utf-8"),
            b"Content-Type: application/pdf",
            b"",
            file_bytes,
            f"--{boundary}--".encode("utf-8"),
            b"",
        ]
        payload = newline.join(parts)

        request_headers = dict(headers)
        request_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        request_headers["Content-Length"] = str(len(payload))

        req = request.Request(endpoint, data=payload, headers=request_headers, method="POST")
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"DashScope file upload failed: HTTP {exc.code} {body_text[:600]}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"DashScope file upload failed: {exc.reason}") from exc

    def _default_get_request(
        self,
        endpoint: str,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        req = request.Request(endpoint, headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"DashScope file status request failed: HTTP {exc.code} {body_text[:600]}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"DashScope file status request failed: {exc.reason}") from exc

    def _normalize_parse_result(self, response_data: dict[str, Any], *, pdf_path: Path) -> dict[str, Any]:
        choices = response_data.get("choices", []) if isinstance(response_data, dict) else []
        message_content: Any = ""
        if choices and isinstance(choices[0], dict):
            message = choices[0].get("message", {})
            if isinstance(message, dict):
                message_content = message.get("content", "")

        response_text = _coerce_response_text(message_content)
        parsed = _extract_json_object(response_text) or {}
        markdown = _normalize_markdown_text(parsed.get("paper_markdown") or parsed.get("markdown"))
        if not markdown:
            markdown = _normalize_markdown_text(response_text)
        if not markdown:
            raise RuntimeError("LLM parser returned empty markdown content.")

        sections = _normalize_section_hints(parsed.get("sections"))
        figures = _normalize_visual_items(parsed.get("figures"), kind="figure")
        tables = _normalize_visual_items(parsed.get("tables"), kind="table")

        usage = response_data.get("usage", {}) if isinstance(response_data, dict) else {}
        return {
            "title": str(parsed.get("title") or pdf_path.stem).strip() or pdf_path.stem,
            "abstract": str(parsed.get("abstract", "") or "").strip(),
            "paper_markdown": markdown,
            "sections": sections,
            "figures": figures,
            "tables": tables,
            "token_usage": usage if isinstance(usage, dict) else {},
            "raw_response": response_data if isinstance(response_data, dict) else {},
        }

    def _build_paper_meta(
        self,
        *,
        pdf_path: Path,
        llm_result_path: Path,
        assets_root: Path,
        total_pages: int,
        normalized: dict[str, Any],
        markdown: str,
        reference_diagnostics: list[dict[str, str]],
    ) -> dict[str, Any]:
        sections = _extract_sections_from_markdown(markdown, normalized.get("sections", []))
        figures = list(normalized.get("figures", []))
        tables = list(normalized.get("tables", []))
        anchors = _build_anchor_records(sections, figures, tables)

        return {
            "doc_id": str(normalized.get("title") or pdf_path.stem).strip() or pdf_path.stem,
            "title": str(normalized.get("title") or pdf_path.stem).strip() or pdf_path.stem,
            "abstract": str(normalized.get("abstract", "") or "").strip(),
            "source_pdf": str(pdf_path.resolve()),
            "parser": "openai_compatible_llm",
            "parser_version": "openai_chat_completions_pdf_v1",
            "status": "SUCCESS",
            "total_pages": total_pages,
            "chunk_count": 1,
            "profile": dict(self.profile),
            "summary": {
                "section_count": len(sections),
                "figure_count": len(figures),
                "table_count": len(tables),
                "anchor_count": len(anchors),
            },
            "sections": sections,
            "anchors": anchors,
            "figures": figures,
            "tables": tables,
            "image_count": len(figures),
            "reference_diagnostics": list(reference_diagnostics or []),
            "artifacts": {
                "llm_result_path": str(llm_result_path.resolve()),
                "assets_dir": str(assets_root.resolve()),
            },
            "origin": _build_origin_metadata(pdf_path),
        }
